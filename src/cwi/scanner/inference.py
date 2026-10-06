"""Project type inference from collected signals."""

from __future__ import annotations

from cwi.domain.enums import Confidence, ProjectType
from cwi.scanner.context import ScanContext


def infer_project_type(ctx: ScanContext) -> tuple[ProjectType, float, str, bool, bool]:
    """Return (type, confidence, reason, backend, frontend)."""
    units = [u for u in ctx.units.values() if u.has_manifest]
    backend_units = [u for u in units if u.backend]
    frontend_units = [u for u in units if u.frontend]
    backend = bool(backend_units)
    frontend = bool(frontend_units)

    def names(us):
        return ", ".join(sorted({f for u in us for f in u.frameworks}))

    if backend and frontend:
        return (
            ProjectType.FULLSTACK,
            Confidence.HIGH,
            f"backend ({names(backend_units)}) and frontend ({names(frontend_units)}) detected",
            True,
            True,
        )
    if ctx.ai_signals:
        reason = "AI SDK detected: " + ", ".join(
            dict.fromkeys(s.split(" (")[0] for s in ctx.ai_signals)
        )
        return ProjectType.AI, Confidence.MEDIUM, reason, backend, frontend
    if backend:
        return (
            ProjectType.BACKEND,
            Confidence.HIGH,
            f"backend framework: {names(backend_units)}",
            True,
            False,
        )
    if frontend:
        return (
            ProjectType.FRONTEND,
            Confidence.HIGH,
            f"frontend framework: {names(frontend_units)}",
            False,
            True,
        )
    if ctx.data_signals:
        reason = "data/ML libraries: " + ", ".join(
            dict.fromkeys(s.split(" (")[0] for s in ctx.data_signals)
        )
        return ProjectType.DATA_ML, Confidence.MEDIUM, reason, False, False
    if ctx.cli_signals:
        return (
            ProjectType.CLI,
            Confidence.MEDIUM,
            "CLI entry point: " + ctx.cli_signals[0],
            False,
            False,
        )
    if ctx.library_signals:
        return (
            ProjectType.LIBRARY,
            Confidence.LOW,
            "package metadata: " + ctx.library_signals[0],
            False,
            False,
        )
    if any(u.language for u in units):
        return ProjectType.OTHER, Confidence.LOW, "no framework signals found", False, False
    return ProjectType.OTHER, Confidence.LOW, "no project signals found", False, False
