"""Explicit compatibility and additive native MCP rendering for optional capabilities."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from spado.catalog.dependency_resolver import find_conflicts, resolve
from spado.catalog.loader import load_catalog
from spado.install.filesystem import FileSystem
from spado.install.json_merge import deep_merge


def codex_server(server: dict) -> dict:
    result = {}
    if "url" in server:
        result["url"] = server["url"]
    elif "command" in server:
        result["command"] = server["command"]
        result["args"] = server.get("args", [])
    else:
        raise ValueError("MCP server needs a URL or command")
    for key, value in server.get("headers", {}).items():
        bearer = re.fullmatch(r"Bearer \$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
        env = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
        if key.lower() == "authorization" and bearer:
            result["bearer_token_env_var"] = bearer[1]
        elif env:
            result.setdefault("env_http_headers", {})[key] = env[1]
        elif "${" in value:
            raise ValueError(f"Unsupported MCP header interpolation: {key}")
        else:
            result.setdefault("http_headers", {})[key] = value
    for key, value in server.get("env", {}).items():
        env = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", value)
        if env and env[1] == key:
            result.setdefault("env_vars", []).append(key)
        elif "${" in value:
            raise ValueError(f"Unsupported MCP environment interpolation: {key}")
        else:
            result.setdefault("env", {})[key] = value
    supported = {"url", "command", "args", "type", "headers", "env"}
    if set(server) - supported:
        raise ValueError("MCP definition contains unsupported host-specific fields")
    return result


def _toml_value(value):
    if isinstance(value, dict):
        return (
            "{ " + ", ".join(f"{json.dumps(k)} = {_toml_value(v)}" for k, v in value.items()) + " }"
        )
    return json.dumps(value)


def render_capabilities(
    root: Path, catalog_path: Path, hosts: list[str], selected: list[str]
) -> dict[str, bytes]:
    if not selected:
        return {}
    catalog = load_catalog(catalog_path)
    refs = resolve(selected, catalog).final
    if find_conflicts(refs, catalog):
        raise ValueError("Selected capabilities have conflicting dependencies")
    output = {}
    mcp, settings = {}, {}
    for ref in refs:
        capability = catalog.require(ref)
        if set(hosts) - set(capability.manifest.hosts):
            raise ValueError(f"{ref} is not declared compatible with all selected hosts")
        for host in hosts:
            for rel in capability.payload_files:
                target = rel
                if host == "codex":
                    if capability.type.value == "skill" and rel.startswith(".claude/skills/"):
                        target = rel.replace(".claude/skills/", ".agents/skills/", 1)
                    elif capability.type.value != "script":
                        raise ValueError(f"{ref}: no reviewed Codex renderer for payload {rel}")
                content = (capability.source_dir / "payload" / rel).read_bytes()
                if target in output and output[target] != content:
                    raise ValueError(f"Conflicting payloads: {target}")
                output[target] = content
        if capability.settings_fragment:
            if "codex" in hosts:
                raise ValueError(f"{ref}: Claude hooks/settings cannot be installed into Codex")
            settings, conflicts = deep_merge(settings, capability.settings_fragment)
            if conflicts:
                raise ValueError("Conflicting settings fragments")
        if capability.mcp_fragment:
            mcp, conflicts = deep_merge(mcp, capability.mcp_fragment.get("mcpServers", {}))
            if conflicts:
                raise ValueError("Conflicting MCP server definitions")
    fs = FileSystem(root)
    for relative, fragment in [
        (".mcp.json", {"mcpServers": mcp}),
        (".claude/settings.json", settings),
    ]:
        if "claude" not in hosts or not (mcp if relative == ".mcp.json" else settings):
            continue
        path = fs.path(relative)
        base = json.loads(path.read_text()) if path.exists() else {}
        merged, conflicts = deep_merge(base, fragment)
        if conflicts:
            raise ValueError(f"Existing host configuration conflicts: {relative}")
        output[relative] = (json.dumps(merged, indent=2) + "\n").encode()
    if "codex" in hosts and mcp:
        path = fs.path(".codex/config.toml")
        text = path.read_text() if path.exists() else ""
        existing = tomllib.loads(text).get("mcp_servers", {})
        for name, server in mcp.items():
            native = codex_server(server)
            if name in existing:
                if existing[name] != native:
                    raise ValueError(f"Existing MCP configuration conflicts: {name}")
                continue
            text += f"\n[mcp_servers.{json.dumps(name)}]\n"
            text += "".join(f"{key} = {_toml_value(value)}\n" for key, value in native.items())
        output[".codex/config.toml"] = text.encode()
    return output
