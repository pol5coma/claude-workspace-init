"""Family (group) manifests: catalog/<type>/<group>/group.json."""

from __future__ import annotations

import json
from pathlib import Path

from cwi import paths
from cwi.authoring.builder import AuthoringError, slugify
from cwi.domain.enums import CapabilityType, ProjectType


def group_dir(catalog_root: Path, cap_type: CapabilityType, group: str) -> Path:
    return catalog_root / cap_type.plural / group


def read_group(path: Path) -> dict:
    try:
        return json.loads((path / paths.GROUP_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthoringError(f"Cannot read {path / paths.GROUP_MANIFEST}: {exc}") from exc


def write_group(path: Path, data: dict) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / paths.GROUP_MANIFEST).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def ensure_group(
    catalog_root: Path,
    cap_type: CapabilityType,
    group: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> Path:
    """Create the family folder + group.json if missing. Refuses to turn a capability into a group."""
    gid = slugify(group)
    if gid != group:
        raise AuthoringError(f"Group names must be lowercase with hyphens (try '{gid}')")
    path = group_dir(catalog_root, cap_type, gid)
    if (path / "cwi.json").exists():
        raise AuthoringError(f"'{gid}' is already a {cap_type.value}, not a group")
    if not (path / paths.GROUP_MANIFEST).is_file():
        write_group(
            path,
            {
                "schema_version": 1,
                "id": gid,
                "type": cap_type.value,
                "name": name or gid.replace("-", " ").capitalize(),
                "description": description or "",
                "defaults": {},
            },
        )
    return path


def set_member_defaults(path: Path, member: str, project_types: list[ProjectType]) -> None:
    """Make `member` a family default for the given project types (adds, never removes)."""
    if not project_types:
        return
    data = read_group(path)
    defaults = data.setdefault("defaults", {})
    for project_type in project_types:
        members = defaults.setdefault(project_type.value, [])
        if member not in members:
            members.append(member)
            members.sort()
    data["defaults"] = dict(sorted(defaults.items()))
    write_group(path, data)


def remove_member_defaults(path: Path, member: str) -> None:
    if not (path / paths.GROUP_MANIFEST).is_file():
        return
    data = read_group(path)
    data["defaults"] = {
        k: [m for m in v if m != member] for k, v in (data.get("defaults") or {}).items()
    }
    data["defaults"] = {k: v for k, v in data["defaults"].items() if v}
    write_group(path, data)
