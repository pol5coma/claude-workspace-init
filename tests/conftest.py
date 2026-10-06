from __future__ import annotations

import pytest

collect_ignore_glob = ["fixtures/*"]


@pytest.fixture
def tmp_repo(tmp_path):
    """Factory: copy a named fixture repository into tmp_path."""
    from tests.helpers import copy_fixture

    def factory(name: str):
        return copy_fixture(name, tmp_path)

    return factory


@pytest.fixture
def real_catalog(tmp_path):
    """A private copy of the bundled catalog (so cleanup can never touch the real one)."""
    from tests.helpers import copy_catalog

    return copy_catalog(tmp_path / "_catalog_source")
