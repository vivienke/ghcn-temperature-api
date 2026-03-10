import pytest
from datetime import date
from fastapi import HTTPException
import asyncio

from app.api.validation import validate_year_range, validate_years_or_raise_http_400
from app.exceptions import InvalidYearRangeError

def test_validate_year_range_ok():
    # gültiger Bereich
    validate_year_range(start_year=2000, end_year=2010, min_year=1800, max_year=2025)


def test_validate_year_range_start_after_end_raises():
    with pytest.raises(InvalidYearRangeError) as exc:
        validate_year_range(start_year=2010, end_year=2000, min_year=1800, max_year=2025)
    assert "startYear" in str(exc.value) and "endYear" in str(exc.value)


def test_validate_year_range_end_year_too_large_raises():
    with pytest.raises(InvalidYearRangeError) as exc:
        validate_year_range(start_year=2000, end_year=2026, min_year=1800, max_year=2025)
    assert "Max allowed" in str(exc.value)


def test_validate_year_range_start_year_too_small_raises():
    with pytest.raises(InvalidYearRangeError) as exc:
        validate_year_range(start_year=1700, end_year=2000, min_year=1800, max_year=2025)
    assert "Min allowed" in str(exc.value)


def test_validate_year_range_allows_boundary_values():
    # start_year == min_year und end_year == max_year müssen erlaubt sein
    validate_year_range(start_year=1800, end_year=2025, min_year=1800, max_year=2025)

def test_validate_year_range_very_large_end_year_raises_max_allowed_message():
    with pytest.raises(InvalidYearRangeError) as exc:
        validate_year_range(start_year=2000, end_year=9999, min_year=1800, max_year=2025)
    assert "Max allowed" in str(exc.value)