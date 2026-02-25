from app.core.exceptions import InvalidYearRangeError

def validate_year_range(start_year: int, end_year: int, *, min_year: int, max_year: int) -> None:
    if start_year > end_year:
        raise InvalidYearRangeError(f"Invalid year range: startYear ({start_year}) must be <= endYear ({end_year}).")
    if end_year > max_year:
        raise InvalidYearRangeError(f"Invalid endYear ({end_year}). Max allowed is {max_year} (previous year).")
    if start_year < min_year:
        raise InvalidYearRangeError(f"Invalid startYear ({start_year}). Min allowed is {min_year} (derived from data).")
