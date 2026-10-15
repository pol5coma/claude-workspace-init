"""Expected errors for catalog and filesystem operations."""


class SPADOError(Exception):
    """Base class for expected SPADO failures."""


class CatalogError(SPADOError):
    """The capability catalog is invalid."""


class UnsafePathError(SPADOError):
    """A path escaped the project root or crossed a symlink."""


class UserCancelled(SPADOError):
    """The user cancelled an interactive catalog operation."""
