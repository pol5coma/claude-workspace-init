from __future__ import annotations

import hashlib
import os
from pathlib import Path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_tree(
    root: Path, ignore: set[str] | frozenset[str] = frozenset({".git"})
) -> dict[str, str]:
    """Map every file under root (relative POSIX path) to its sha256. Used by invariant tests."""
    result: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root)
        dirnames[:] = sorted(
            d for d in dirnames if d not in ignore and (rel_dir / d).as_posix() not in ignore
        )
        for filename in filenames:
            rel = (rel_dir / filename).as_posix()
            if rel in ignore:
                continue
            full = Path(dirpath) / filename
            result[rel] = "symlink:" + os.readlink(full) if full.is_symlink() else sha256_file(full)
    return result
