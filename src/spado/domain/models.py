"""Models for reusable SPADO capabilities and catalog groups."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from spado.domain.enums import CapabilityType, Category, ProjectType


class RecommendationRules(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_types: list[ProjectType] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    require_technology: bool = False  # only recommend when a technology matches


class EnvRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    required: bool = True


class Requirements(BaseModel):
    model_config = ConfigDict(extra="forbid")

    env: list[EnvRequirement] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)  # executables needed at runtime, e.g. "node"


SUPPORTED_CATALOG_SCHEMA = 1


class CapabilityManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    type: CapabilityType
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    categories: list[Category] = Field(default_factory=list)
    hosts: list[str] = Field(default_factory=lambda: ["claude"])
    default_selected: bool = False
    recommendation: RecommendationRules | None = None
    dependencies: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    requirements: Requirements = Field(default_factory=Requirements)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("id must be lowercase letters, digits and hyphens")
        return value

    @property
    def ref(self) -> str:
        return f"{self.type.value}:{self.id}"


class CapabilityGroup(BaseModel):
    """A family of capabilities of one type, stored as catalog/<type>/<group>/<id>/.

    `defaults` stores suggested members by project type; current installation is explicit.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: int
    id: str
    type: CapabilityType
    name: str
    description: str = ""
    defaults: dict[ProjectType, list[str]] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _valid_id(cls, value: str) -> str:
        import re

        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
            raise ValueError("id must be lowercase letters, digits and hyphens")
        return value


class Capability(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    manifest: CapabilityManifest
    source_dir: Path
    group: str | None = None  # family folder name, e.g. "development-agents"
    payload_files: list[str] = Field(default_factory=list)  # POSIX paths relative to payload/
    settings_fragment: dict[str, Any] | None = None
    mcp_fragment: dict[str, Any] | None = None

    @property
    def ref(self) -> str:
        return self.manifest.ref

    @property
    def id(self) -> str:
        return self.manifest.id

    @property
    def type(self) -> CapabilityType:
        return self.manifest.type

    @property
    def payload_dir(self) -> Path:
        return self.source_dir / "payload"


class Catalog(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    root: Path
    capabilities: list[Capability] = Field(default_factory=list)
    groups: list[CapabilityGroup] = Field(default_factory=list)

    def group(self, cap_type: CapabilityType, group_id: str | None) -> CapabilityGroup | None:
        if group_id is None:
            return None
        return next((g for g in self.groups if g.type == cap_type and g.id == group_id), None)

    def get(self, ref: str) -> Capability | None:
        for cap in self.capabilities:
            if cap.ref == ref:
                return cap
        return None

    def require(self, ref: str) -> Capability:
        cap = self.get(ref)
        if cap is None:
            from spado.domain.errors import CatalogError

            raise CatalogError(f"Unknown capability: {ref}")
        return cap

    def by_type(self, cap_type: CapabilityType) -> list[Capability]:
        # Ungrouped capabilities first, then each family alphabetically.
        return sorted(
            (c for c in self.capabilities if c.type == cap_type),
            key=lambda c: (c.group is not None, c.group or "", c.id),
        )

    @property
    def refs(self) -> list[str]:
        return [c.ref for c in self.capabilities]
