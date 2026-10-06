"""Write a built capability into the catalog atomically and validate the whole catalog."""

from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from cwi.authoring.builder import AuthoringError, BuiltCapability
from cwi.catalog.loader import load_catalog
from cwi.domain.enums import CapabilityType
from cwi.domain.errors import CatalogError


def existing_ids(catalog_root: Path) -> dict[str, str]:
    """id -> ref for every capability folder, without requiring the catalog to be valid."""
    found: dict[str, str] = {}
    for cap_type in CapabilityType:
        type_dir = catalog_root / cap_type.plural
        if not type_dir.is_dir():
            continue
        for child in type_dir.iterdir():
            if child.is_dir() and not child.name.startswith("."):
                found.setdefault(child.name, f"{cap_type.value}:{child.name}")
    return found


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
    ids = existing_ids(catalog_root)
    if built.id in ids:
        owner = ids[built.id]
        if owner != built.ref:
            raise AuthoringError(
                f"The id '{built.id}' is already used by {owner}. Ids must be unique across types; pass --id."
            )
        if not force:
            raise AuthoringError(f"{built.ref} already exists. Pass --force to replace it.")

    type_dir = catalog_root / built.cap_type.plural
    type_dir.mkdir(parents=True, exist_ok=True)
    target = type_dir / built.id
    token = uuid.uuid4().hex[:8]
    staging = type_dir / f".{built.id}.cwi-new-{token}"
    backup = type_dir / f".{built.id}.cwi-old-{token}"
    try:
        _stage(built, staging)
        if target.exists():
            target.rename(backup)
        staging.rename(target)
        try:
            load_catalog(catalog_root)
        except CatalogError as exc:
            shutil.rmtree(target, ignore_errors=True)
            if backup.exists():
                backup.rename(target)
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
        cap_type = CapabilityType(kind)
    except ValueError as exc:
        raise AuthoringError(f"Use a reference like skill:testing (got '{ref}')") from exc
    target = catalog_root / cap_type.plural / cid
    if not (target / "cwi.json").is_file() or target.is_symlink():
        raise AuthoringError(f"{ref} is not in the catalog ({target})")
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
    return target
