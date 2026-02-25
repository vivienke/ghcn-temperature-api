"""Custom exceptions for the GHCN Temperature API."""


class StationNotFoundError(Exception):
    """Raised when a requested station is not found in the metadata."""
    pass


class InvalidYearRangeError(Exception):
    """Raised when the provided year range is invalid."""
    pass


class DataUnavailableError(Exception):
    """Raised when required data (e.g., metadata or station files) is not available."""
    pass
