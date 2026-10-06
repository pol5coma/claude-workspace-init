"""Explicit domain exceptions. Expected errors become clean CLI messages."""


class CWIError(Exception):
    """Base class for every expected CWI failure."""


class CatalogError(CWIError):
    """The bundled catalog is invalid."""


class ScanError(CWIError):
    """The project scan failed."""


class ConflictError(CWIError):
    """A conflict needs a user decision and none was provided."""


class PlanError(CWIError):
    """The installation plan could not be built."""


class ApplyError(CWIError):
    """Applying the plan failed (changes rolled back)."""


class ValidationError(CWIError):
    """The resulting workspace failed validation."""


class StateError(CWIError):
    """The CWI state file is unreadable or unsupported."""


class UnsafePathError(CWIError):
    """A path escaped the project root or crossed a symlink."""


class UserCancelled(CWIError):
    """The user cancelled the flow. Nothing was changed."""
