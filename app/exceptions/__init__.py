"""Custom exceptions module."""

from app.exceptions.exceptions import (
    StationNotFoundError,
    InvalidYearRangeError,
    DataUnavailableError,
)

__all__ = [
    "StationNotFoundError",
    "InvalidYearRangeError",
    "DataUnavailableError",
]
