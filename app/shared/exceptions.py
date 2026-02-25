"""Custom exceptions for the GHCN Temperature API."""


class StationNotFoundError(Exception):
    """Raised when a requested station is not found in the metadata."""


class InvalidYearRangeError(Exception):
    """Raised when the provided year range is invalid."""


class DataUnavailableError(Exception):
    """Raised when required data (e.g., metadata or station files) is not available."""
