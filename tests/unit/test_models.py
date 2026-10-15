from spado.domain.enums import CapabilityType
from spado.domain.models import CapabilityManifest


def test_manifest_ref_and_validation():
    m = CapabilityManifest(
        schema_version=1, id="testing", type="skill", name="Testing", description="d"
    )
    assert m.ref == "skill:testing"
    assert m.type is CapabilityType.SKILL


def test_manifest_rejects_bad_id():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CapabilityManifest(schema_version=1, id="../evil", type="skill", name="x", description="d")


def test_manifest_rejects_unknown_fields():
    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        CapabilityManifest(
            schema_version=1, id="x", type="skill", name="x", description="d", surprise=True
        )
