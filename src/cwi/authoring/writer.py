"""Write a built capability into the catalog atomically and validate the whole catalog."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from cwi import paths
from cwi.authoring.builder import AuthoringError, BuiltCapability
from cwi.authoring.groups import (
    ensure_group,
    group_dir,
    read_group,
    remove_member_defaults,
    set_member_defaults,
    write_group,
)
from cwi.catalog.loader import load_catalog
from cwi.domain.enums import CapabilityType
from cwi.domain.errors import CatalogError


def capability_dirs(catalog_root: Path) -> dict[str, tuple[str, Path]]:
    """id -> (ref, folder) for every capability, grouped or not, without validating the catalog."""
    found: dict[str, tuple[str, Path]] = {}
    for cap_type in CapabilityType:
        type_dir = catalog_root / cap_type.plural
        if not type_dir.is_dir():
            continue
        for child in sorted(type_dir.iterdir()):
            if not child.is_dir() or child.name.startswith("."):
                continue
            if (child / paths.GROUP_MANIFEST).is_file():
                for member in sorted(child.iterdir()):
                    if member.is_dir() and not member.name.startswith("."):
                        found.setdefault(member.name, (f"{cap_type.value}:{member.name}", member))
            else:
                found.setdefault(child.name, (f"{cap_type.value}:{child.name}", child))
    return found


def existing_ids(catalog_root: Path) -> dict[str, str]:
    return {cid: ref for cid, (ref, _) in capability_dirs(catalog_root).items()}


def ensure_catalog_valid(catalog_root: Path) -> None:
    if not catalog_root.is_dir():
        raise AuthoringError(
            f"Catalog not found: {catalog_root}. Run from the template root or pass --catalog."
        )
    try:
        load_catalog(catalog_root)
    except CatalogError as exc:
        raise AuthoringError(
            f"The catalog is already invalid; fix it first (cwi catalog validate).\n{exc}"
        ) from exc


def _stage(built: BuiltCapability, directory: Path) -> None:
    directory.mkdir(parents=True)
    (directory / "cwi.json").write_text(
        json.dumps(built.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    for name, fragment in built.fragments.items():
        (directory / name).write_text(
            json.dumps(fragment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for rel, source in sorted(built.payload.items()):
        target = directory / "payload" / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(source, Path):
            shutil.copyfile(source, target)
            shutil.copymode(source, target)
        else:
            target.write_text(source, encoding="utf-8")


def write_capability(catalog_root: Path, built: BuiltCapability, *, force: bool = False) -> Path:
    """Stage in a hidden temp folder, swap into place, validate the catalog, roll back on failure."""
    catalog_root = catalog_root.resolve()
    ensure_catalog_valid(catalog_root)
    known = capability_dirs(catalog_root)
    ids = {cid: ref for cid, (ref, _) in known.items()}
    if built.group and built.group in ids:
        raise AuthoringError(f"'{built.group}' is a capability id; pick another group name")
    if built.id in ids:
        owner = ids[built.id]
        if owner != built.ref:
            raise AuthoringError(
                f"The id '{built.id}' is already used by {owner}. Ids must be unique across types; pass --id."
            )
        if not force:
            raise AuthoringError(f"{built.ref} already exists. Pass --force to replace it.")

    created_group = False
    if built.group:
        group_path = group_dir(catalog_root, built.cap_type, built.group)
        created_group = not (group_path / paths.GROUP_MANIFEST).is_file()
        type_dir = ensure_group(catalog_root, built.cap_type, built.group)
        group_backup = read_group(type_dir)
    else:
        type_dir = catalog_root / built.cap_type.plural
        type_dir.mkdir(parents=True, exist_ok=True)
    previous = known.get(built.id, (None, None))[1]
    if previous is not None and previous.parent != type_dir:
        raise AuthoringError(
            f"{built.ref} lives in {previous.parent.relative_to(catalog_root)}; remove it first to move it to another group"
        )
    target = type_dir / built.id
    token = uuid.uuid4().hex[:8]
    staging = type_dir / f".{built.id}.cwi-new-{token}"
    backup = type_dir / f".{built.id}.cwi-old-{token}"
    try:
        _stage(built, staging)
        if target.exists():
            target.rename(backup)
        staging.rename(target)
        if built.group:
            set_member_defaults(type_dir, built.id, built.group_defaults)
        try:
            load_catalog(catalog_root)
        except CatalogError as exc:
            shutil.rmtree(target, ignore_errors=True)
            if backup.exists():
                backup.rename(target)
            if built.group:
                if created_group:
                    shutil.rmtree(type_dir, ignore_errors=True)
                else:
                    write_group(type_dir, group_backup)
            raise AuthoringError(
                f"The new capability is invalid, nothing was added.\n{exc}"
            ) from exc
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if backup.exists() and target.exists():
            shutil.rmtree(backup, ignore_errors=True)
    return target


def remove_capability(catalog_root: Path, ref: str, *, force: bool = False) -> Path:
    catalog_root = catalog_root.resolve()
    kind, _, cid = ref.partition(":")
    try:
        CapabilityType(kind)
    except ValueError as exc:
        raise AuthoringError(f"Use a reference like skill:testing (got '{ref}')") from exc
    entry = capability_dirs(catalog_root).get(cid)
    if (
        entry is None
        or entry[0] != ref
        or not (entry[1] / "cwi.json").is_file()
        or entry[1].is_symlink()
    ):
        raise AuthoringError(f"{ref} is not in the catalog")
    target = entry[1]
    in_group = (target.parent / paths.GROUP_MANIFEST).is_file()
    dependents = []
    try:
        catalog = load_catalog(catalog_root)
        dependents = [c.ref for c in catalog.capabilities if ref in c.manifest.dependencies]
    except CatalogError:
        pass
    if dependents and not force:
        raise AuthoringError(
            f"{ref} is required by {', '.join(dependents)}. Pass --force to remove it anyway."
        )
    shutil.rmtree(target)
    if in_group:
        remove_member_defaults(target.parent, cid)
        remaining = [
            p for p in target.parent.iterdir() if p.is_dir() and not p.name.startswith(".")
        ]
        if not remaining:
            shutil.rmtree(target.parent)  # last member gone: drop the empty family
    return target
