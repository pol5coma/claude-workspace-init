"""Explicit domain exceptions. Expected errors become clean CLI messages."""


class SPADOError(Exception):
    """Base class for every expected SPADO failure."""


class CatalogError(SPADOError):
    """The bundled catalog is invalid."""


class ScanError(SPADOError):
    """The project scan failed."""


class ConflictError(SPADOError):
    """A conflict needs a user decision and none was provided."""


class PlanError(SPADOError):
    """The installation plan could not be built."""


class ApplyError(SPADOError):
    """Applying the plan failed (changes rolled back)."""


class ValidationError(SPADOError):
    """The resulting workspace failed validation."""


class StateError(SPADOError):
    """The SPADO state file is unreadable or unsupported."""


class UnsafePathError(SPADOError):
    """A path escaped the project root or crossed a symlink."""


class UserCancelled(SPADOError):
    """The user cancelled the flow. Nothing was changed."""
