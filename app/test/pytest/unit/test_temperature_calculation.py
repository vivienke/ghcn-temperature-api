import pytest
import pandas as pd
import numpy as np
from app.logic.temperature_calculation import (
    calculate_period_averages,
    build_empty_series,
    apply_series_values,
    _round_or_none,
)


class TestRoundOrNone:
    def test_round_or_none_normal_value(self):
        """Test rounding of normal float values"""
        assert _round_or_none(23.456) == 23.5
        assert _round_or_none(10.0) == 10.0
        assert _round_or_none(-5.54) == -5.5

    def test_round_or_none_none_input(self):
        """Test that None returns None"""
        assert _round_or_none(None) is None

    def test_round_or_none_nan_input(self):
        """Test that NaN returns None"""
        assert _round_or_none(np.nan) is None
        assert _round_or_none(float('nan')) is None

    def test_round_or_none_zero(self):
        """Test rounding of zero"""
        assert _round_or_none(0.0) == 0.0
        assert _round_or_none(0.05) == 0.1

    def test_round_or_none_negative_values(self):
        """Test rounding of negative values"""
        assert _round_or_none(-23.456) == -23.5
        assert _round_or_none(-0.05) == -0.1


class TestBuildEmptySeries:
    def test_build_empty_series_basic(self):
        """Test basic series structure creation"""
        years = [2000, 2001, 2002]
        periods = ("YEAR", "WINTER", "SPRING")
        elements = ("TMIN", "TMAX")

        series = build_empty_series(years, periods, elements)

        # Should have 6 keys (3 periods * 2 elements)
        assert len(series) == 6
        assert "YEAR_TMIN" in series
        assert "YEAR_TMAX" in series
        assert "WINTER_TMIN" in series
        assert "SPRING_TMAX" in series

    def test_build_empty_series_values_are_none(self):
        """Test that all initial values are None"""
        years = [2000, 2001]
        periods = ("YEAR",)
        elements = ("TMIN",)

        series = build_empty_series(years, periods, elements)

        assert series["YEAR_TMIN"] == [None, None]
        assert all(v is None for v in series["YEAR_TMIN"])

    def test_build_empty_series_correct_length(self):
        """Test that series have correct length based on years"""
        years = list(range(1990, 2020))  # 30 years
        periods = ("YEAR",)
        elements = ("TMIN", "TMAX")

        series = build_empty_series(years, periods, elements)

        assert len(series["YEAR_TMIN"]) == 30
        assert len(series["YEAR_TMAX"]) == 30

    def test_build_empty_series_empty_years(self):
        """Test edge case with empty years"""
        years = []
        periods = ("YEAR",)
        elements = ("TMIN",)

        series = build_empty_series(years, periods, elements)

        assert series["YEAR_TMIN"] == []


class TestCalculatePeriodAverages:
    def test_calculate_period_averages_single_period(self):
        """Test averaging for a single period"""
        data = {
            "periodYear": [2000, 2000],
            "period": ["YEAR", "YEAR"],
            "ELEMENT": ["TMIN", "TMIN"],
            "temperature_celsius": [5.0, 7.0],
        }
        df = pd.DataFrame(data)

        result = calculate_period_averages(df)

        assert len(result) == 1
        assert result.iloc[0]["TMIN"] == 6.0
        assert result.iloc[0]["periodYear"] == 2000

    def test_calculate_period_averages_multiple_elements(self):
        """Test averaging with TMIN and TMAX"""
        data = {
            "periodYear": [2000, 2000, 2000, 2000],
            "period": ["YEAR", "YEAR", "YEAR", "YEAR"],
            "ELEMENT": ["TMIN", "TMIN", "TMAX", "TMAX"],
            "temperature_celsius": [10.0, 12.0, 20.0, 22.0],
        }
        df = pd.DataFrame(data)

        result = calculate_period_averages(df)

        assert len(result) == 1
        assert result.iloc[0]["TMIN"] == 11.0
        assert result.iloc[0]["TMAX"] == 21.0

    def test_calculate_period_averages_multiple_years_and_periods(self):
        """Test averaging across multiple years and seasons"""
        data = {
            "periodYear": [2000, 2000, 2001, 2001],
            "period": ["YEAR", "WINTER", "YEAR", "WINTER"],
            "ELEMENT": ["TMIN", "TMIN", "TMIN", "TMIN"],
            "temperature_celsius": [10.0, 5.0, 15.0, 3.0],
        }
        df = pd.DataFrame(data)

        result = calculate_period_averages(df)

        assert len(result) == 4
        # Check YEAR 2000
        year_2000 = result[(result["periodYear"] == 2000) & (result["period"] == "YEAR")]
        assert len(year_2000) == 1
        assert year_2000.iloc[0]["TMIN"] == 10.0

    def test_calculate_period_averages_with_nan(self):
        """Test that NaN values are handled correctly by mean()"""
        data = {
            "periodYear": [2000, 2000, 2000],
            "period": ["YEAR", "YEAR", "YEAR"],
            "ELEMENT": ["TMIN", "TMIN", "TMIN"],
            "temperature_celsius": [10.0, np.nan, 20.0],
        }
        df = pd.DataFrame(data)

        result = calculate_period_averages(df)

        # pandas mean() ignores NaN by default
        assert result.iloc[0]["TMIN"] == 15.0


class TestApplySeriesValues:
    def test_apply_series_values_basic(self):
        """Test basic value application"""
        series = build_empty_series([2000, 2001], ("YEAR",), ("TMIN", "TMAX"))
        period_avg_data = {
            "periodYear": [2000],
            "period": ["YEAR"],
            "TMIN": [10.5],
            "TMAX": [20.0],
        }
        period_avg_df = pd.DataFrame(period_avg_data)

        apply_series_values(series, [2000, 2001], period_avg_df)

        assert series["YEAR_TMIN"][0] == 10.5
        assert series["YEAR_TMIN"][1] is None
        assert series["YEAR_TMAX"][0] == 20.0

    def test_apply_series_values_multiple_years(self):
        """Test applying values across multiple years"""
        series = build_empty_series(
            [2000, 2001, 2002], ("YEAR",), ("TMIN", "TMAX")
        )
        period_avg_data = {
            "periodYear": [2000, 2001, 2002],
            "period": ["YEAR", "YEAR", "YEAR"],
            "TMIN": [10.0, 12.0, 11.0],
            "TMAX": [20.0, 22.0, 21.0],
        }
        period_avg_df = pd.DataFrame(period_avg_data)

        apply_series_values(series, [2000, 2001, 2002], period_avg_df)

        assert series["YEAR_TMIN"] == [10.0, 12.0, 11.0]
        assert series["YEAR_TMAX"] == [20.0, 22.0, 21.0]

    def test_apply_series_values_out_of_range_ignored(self):
        """Test that out-of-range data is ignored"""
        series = build_empty_series([2000, 2001], ("YEAR",), ("TMIN", "TMAX"))
        period_avg_data = {
            "periodYear": [1999, 2000, 2001, 2002],
            "period": ["YEAR", "YEAR", "YEAR", "YEAR"],
            "TMIN": [5.0, 10.0, 12.0, 15.0],
            "TMAX": [15.0, 20.0, 22.0, 25.0],
        }
        period_avg_df = pd.DataFrame(period_avg_data)

        apply_series_values(series, [2000, 2001], period_avg_df)

        # Only 2000 and 2001 should be applied
        assert series["YEAR_TMIN"] == [10.0, 12.0]
        assert series["YEAR_TMAX"] == [20.0, 22.0]

    def test_apply_series_values_non_numeric_ignored(self):
        """Test that non-numeric values (NaN) are handled"""
        series = build_empty_series([2000, 2001], ("YEAR",), ("TMIN", "TMAX"))
        period_avg_data = {
            "periodYear": [2000, 2001],
            "period": ["YEAR", "YEAR"],
            "TMIN": [10.0, np.nan],
            "TMAX": [20.0, 30.0],
        }
        period_avg_df = pd.DataFrame(period_avg_data)

        apply_series_values(series, [2000, 2001], period_avg_df)

        assert series["YEAR_TMIN"][0] == 10.0
        assert series["YEAR_TMIN"][1] is None

    def test_apply_series_values_multiple_periods(self):
        """Test applying values for different periods"""
        series = build_empty_series(
            [2000], ("YEAR", "WINTER", "SPRING"), ("TMIN", "TMAX")
        )
        period_avg_data = {
            "periodYear": [2000, 2000, 2000],
            "period": ["YEAR", "WINTER", "SPRING"],
            "TMIN": [10.0, 3.0, 8.0],
            "TMAX": [20.0, 8.0, 18.0],
        }
        period_avg_df = pd.DataFrame(period_avg_data)

        apply_series_values(series, [2000], period_avg_df)

        assert series["YEAR_TMIN"][0] == 10.0
        assert series["WINTER_TMIN"][0] == 3.0
        assert series["SPRING_TMIN"][0] == 8.0
        assert series["YEAR_TMAX"][0] == 20.0
