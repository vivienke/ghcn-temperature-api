import pytest
from app.logic.station_search import _covers_year_range


class TestCoversYearRange:
    def test_covers_exact_match(self):
        """Test exact match of requested range"""
        # Station data: 1900-2000, request: 1900-2000
        assert _covers_year_range(
            first_year=1900, last_year=2000,
            start_year=1900, end_year=2000
        ) is True

    def test_covers_station_within_range(self):
        """Test station data covers requested range"""
        # Station data: 1800-2100, request: 1900-2000
        assert _covers_year_range(
            first_year=1800, last_year=2100,
            start_year=1900, end_year=2000
        ) is True

    def test_covers_insufficient_first_year(self):
        """Test insufficient first year coverage"""
        # Station data: 1950-2000, request: 1900-2000
        assert _covers_year_range(
            first_year=1950, last_year=2000,
            start_year=1900, end_year=2000
        ) is False

    def test_covers_insufficient_last_year(self):
        """Test insufficient last year coverage"""
        # Station data: 1900-1950, request: 1900-2000
        assert _covers_year_range(
            first_year=1900, last_year=1950,
            start_year=1900, end_year=2000
        ) is False

    def test_covers_both_insufficient(self):
        """Test insufficient coverage on both ends"""
        # Station data: 1950-1999, request: 1900-2000
        assert _covers_year_range(
            first_year=1950, last_year=1999,
            start_year=1900, end_year=2000
        ) is False

    def test_covers_single_year(self):
        """Test with single year request"""
        # Station data: 1900-2000, request: 1950-1950
        assert _covers_year_range(
            first_year=1900, last_year=2000,
            start_year=1950, end_year=1950
        ) is True

    def test_covers_single_year_insufficient(self):
        """Test single year request insufficient"""
        # Station data: 1900-1949, request: 1950-1950
        assert _covers_year_range(
            first_year=1900, last_year=1949,
            start_year=1950, end_year=1950
        ) is False

    def test_covers_off_by_one_first_year(self):
        """Test off-by-one error first year"""
        # Station data: 1901-2000, request: 1900-2000
        assert _covers_year_range(
            first_year=1901, last_year=2000,
            start_year=1900, end_year=2000
        ) is False

    def test_covers_off_by_one_last_year(self):
        """Test off-by-one error last year"""
        # Station data: 1900-1999, request: 1900-2000
        assert _covers_year_range(
            first_year=1900, last_year=1999,
            start_year=1900, end_year=2000
        ) is False

    def test_covers_large_range(self):
        """Test with very large ranges"""
        # Station data: 1700-2100, request: 1800-2000
        assert _covers_year_range(
            first_year=1700, last_year=2100,
            start_year=1800, end_year=2000
        ) is True

    def test_covers_boundary_conditions(self):
        """Test boundary at exact limits"""
        # Station data: 1900-2000, request both at boundaries
        assert _covers_year_range(
            first_year=1900, last_year=2000,
            start_year=1900, end_year=2000
        ) is True

        # Just outside on one side
        assert _covers_year_range(
            first_year=1899, last_year=2000,
            start_year=1900, end_year=2000
        ) is True

        assert _covers_year_range(
            first_year=1900, last_year=2001,
            start_year=1900, end_year=2000
        ) is True

    def test_covers_zero_year_edge_case(self):
        """Test with year 0 (edge case)"""
        # This is a mathematical edge case
        assert _covers_year_range(
            first_year=0, last_year=2000,
            start_year=1000, end_year=1500
        ) is True
