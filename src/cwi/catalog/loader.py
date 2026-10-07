"""Generic catalog loader: one code path for every capability type."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from cwi import paths
from cwi.domain.enums import CapabilityType
from cwi.domain.errors import CatalogError
from cwi.domain.models import (
    SUPPORTED_CATALOG_SCHEMA,
    Capability,
    CapabilityGroup,
    CapabilityManifest,
    Catalog,
)

MANIFEST_NAME = "cwi.json"
SETTINGS_FRAGMENT = "settings.fragment.json"
JUNK_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
JUNK_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache"}
MCP_FRAGMENT = "mcp.fragment.json"


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Invalid JSON in {path}: {exc.msg} (line {exc.lineno})") from exc
    except OSError as exc:
        raise CatalogError(f"Cannot read {path}: {exc}") from exc


def load_manifest(path: Path) -> CapabilityManifest:
    if not path.is_file():
        raise CatalogError(f"Missing manifest: {path}")
    data = _read_json(path)
    if not isinstance(data, dict):
        raise CatalogError(f"Manifest must be a JSON object: {path}")
    version = data.get("schema_version")
    if version != SUPPORTED_CATALOG_SCHEMA:
        raise CatalogError(
            f"Unsupported catalog schema version: {version} ({path}).\n"
            f"This CWI version supports schema version {SUPPORTED_CATALOG_SCHEMA}. "
            "Upgrade CWI before continuing."
        )
    try:
        return CapabilityManifest.model_validate(data)
    except PydanticValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise CatalogError(f"Invalid manifest {path}: {problems}") from exc


def _list_payload(payload_dir: Path) -> list[str]:
    """List payload files as POSIX paths. Symlinks are reported, not followed."""
    files: list[str] = []
    if not payload_dir.exists():
        return files
    for path in sorted(payload_dir.rglob("*")):
        if path.is_symlink():
            raise CatalogError(f"Catalog payload contains a symlink, which is not allowed: {path}")
        rel = path.relative_to(payload_dir)
        if (
            path.name in JUNK_NAMES
            or path.suffix == ".pyc"
            or any(p in JUNK_DIRS for p in rel.parts)
        ):
            continue
        if path.is_file():
            files.append(rel.as_posix())
    return files


def load_group(group_dir: Path, cap_type: CapabilityType) -> CapabilityGroup:
    path = group_dir / paths.GROUP_MANIFEST
    data = _read_json(path)
    if not isinstance(data, dict):
        raise CatalogError(f"Group manifest must be a JSON object: {path}")
    if data.get("schema_version") != SUPPORTED_CATALOG_SCHEMA:
        raise CatalogError(
            f"Unsupported catalog schema version: {data.get('schema_version')} ({path}).\n"
            f"This CWI version supports schema version {SUPPORTED_CATALOG_SCHEMA}. Upgrade CWI before continuing."
        )
    try:
        group = CapabilityGroup.model_validate(data)
    except PydanticValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()
        )
        raise CatalogError(f"Invalid group manifest {path}: {problems}") from exc
    if group.id != group_dir.name:
        raise CatalogError(
            f"{group_dir}: group id '{group.id}' does not match directory name '{group_dir.name}'"
        )
    if group.type != cap_type:
        raise CatalogError(
            f"{group_dir}: group type '{group.type}' does not match directory '{cap_type.plural}/'"
        )
    return group


def _capability_dirs(type_dir: Path) -> list[tuple[Path, str | None]]:
    """(capability_dir, group) pairs. A folder with group.json is a family of capabilities."""
    found: list[tuple[Path, str | None]] = []
    for child in sorted(type_dir.iterdir()):
        if child.name.startswith(".") or not child.is_dir():
            continue
        if child.is_symlink():
            raise CatalogError(f"Catalog directory is a symlink: {child}")
        if (child / paths.GROUP_MANIFEST).is_file():
            if (child / MANIFEST_NAME).exists():
                raise CatalogError(
                    f"{child}: a folder cannot be both a capability (cwi.json) and a group (group.json)"
                )
            for member in sorted(child.iterdir()):
                if member.name.startswith(".") or not member.is_dir():
                    continue
                if (member / paths.GROUP_MANIFEST).exists():
                    raise CatalogError(f"{member}: groups cannot be nested")
                found.append((member, child.name))
        else:
            found.append((child, None))
    return found


def load_capability(capability_dir: Path, group: str | None = None) -> Capability:
    if capability_dir.is_symlink():
        raise CatalogError(f"Catalog capability directory is a symlink: {capability_dir}")
    manifest = load_manifest(capability_dir / MANIFEST_NAME)
    payload_dir = capability_dir / "payload"
    if payload_dir.is_symlink():
        raise CatalogError(f"Catalog payload directory is a symlink: {payload_dir}")
    settings_fragment = None
    mcp_fragment = None
    if (capability_dir / SETTINGS_FRAGMENT).exists():
        settings_fragment = _read_json(capability_dir / SETTINGS_FRAGMENT)
    if (capability_dir / MCP_FRAGMENT).exists():
        mcp_fragment = _read_json(capability_dir / MCP_FRAGMENT)
    return Capability(
        manifest=manifest,
        source_dir=capability_dir,
        group=group,
        payload_files=_list_payload(payload_dir),
        settings_fragment=settings_fragment,
        mcp_fragment=mcp_fragment,
    )


def load_catalog(catalog_root: Path, *, validate: bool = True) -> Catalog:
    """Load every capability under `catalog_root` and fail early on invalid data."""
    if not catalog_root.is_dir():
        raise CatalogError(f"Catalog directory not found: {catalog_root}")
    capabilities: list[Capability] = []
    groups: list[CapabilityGroup] = []
    for cap_type in CapabilityType:
        type_dir = catalog_root / cap_type.plural
        if not type_dir.is_dir():
            continue
        for child in sorted(type_dir.iterdir()):
            if (
                child.is_dir()
                and not child.name.startswith(".")
                and (child / paths.GROUP_MANIFEST).is_file()
            ):
                groups.append(load_group(child, cap_type))
        for capability_dir, group in _capability_dirs(type_dir):
            capability = load_capability(capability_dir, group)
            if capability.type != cap_type:
                raise CatalogError(
                    f"{capability_dir}: manifest type '{capability.type}' does not match "
                    f"directory '{cap_type.plural}/'"
                )
            if capability.id != capability_dir.name:
                raise CatalogError(
                    f"{capability_dir}: manifest id '{capability.id}' does not match "
                    f"directory name '{capability_dir.name}'"
                )
            capabilities.append(capability)
    catalog = Catalog(root=catalog_root, capabilities=capabilities, groups=groups)
    if validate:
        from cwi.catalog.validator import validate_catalog

        validate_catalog(catalog)
    return catalog
