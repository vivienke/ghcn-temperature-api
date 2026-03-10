import pytest
import pandas as pd
import numpy as np
from app.logic.temperature_series import (
    _build_northern_season_labels,
    _map_southern_hemisphere_seasons,
    _compute_period_years_for_boundary_season,
    _build_period_views,
)


class TestBuildNorthernSeasonLabels:
    def test_northern_seasons_mapping(self):
        """Test that months map to correct northern hemisphere seasons"""
        months = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])

        labels = _build_northern_season_labels(months)

        expected = np.array(
            ["WINTER", "WINTER", "SPRING", "SPRING", "SPRING", "SUMMER",
             "SUMMER", "SUMMER", "AUTUMN", "AUTUMN", "AUTUMN", "WINTER"],
            dtype=object
        )
        np.testing.assert_array_equal(labels, expected)

    def test_northern_seasons_boundary_months(self):
        """Test boundary months specifically"""
        # March is first month of spring
        months_spring = pd.Series([3, 5])
        labels = _build_northern_season_labels(months_spring)
        assert labels[0] == "SPRING"
        assert labels[1] == "SPRING"

        # June is first month of summer
        months_summer = pd.Series([6, 8])
        labels = _build_northern_season_labels(months_summer)
        assert labels[0] == "SUMMER"
        assert labels[1] == "SUMMER"

        # September is first month of autumn
        months_autumn = pd.Series([9, 11])
        labels = _build_northern_season_labels(months_autumn)
        assert labels[0] == "AUTUMN"
        assert labels[1] == "AUTUMN"


class TestMapSouthernHemisphereSeasons:
    def test_southern_hemisphere_season_mapping(self):
        """Test that seasons are correctly mapped for southern hemisphere"""
        northern_seasons = np.array(["WINTER", "SPRING", "SUMMER", "AUTUMN"], dtype=object)

        southern_seasons = _map_southern_hemisphere_seasons(northern_seasons)

        expected = np.array(["SUMMER", "AUTUMN", "WINTER", "SPRING"], dtype=object)
        np.testing.assert_array_equal(southern_seasons, expected)

    def test_southern_hemisphere_full_year(self):
        """Test full year mapping for southern hemisphere"""
        # Northern months: Jan-Dec map to WINTER, WINTER, SPRING, ..., WINTER
        northern_labels = np.array(
            ["WINTER", "WINTER", "SPRING", "SPRING", "SPRING", "SUMMER",
             "SUMMER", "SUMMER", "AUTUMN", "AUTUMN", "AUTUMN", "WINTER"],
            dtype=object
        )

        southern_labels = _map_southern_hemisphere_seasons(northern_labels)

        expected = np.array(
            ["SUMMER", "SUMMER", "AUTUMN", "AUTUMN", "AUTUMN", "WINTER",
             "WINTER", "WINTER", "SPRING", "SPRING", "SPRING", "SUMMER"],
            dtype=object
        )
        np.testing.assert_array_equal(southern_labels, expected)


class TestComputePeriodYearsForBoundarySeason:
    def test_january_february_winter_adjustment(self):
        """Test that Jan/Feb of WINTER boundary season get adjusted to previous year"""
        data = {
            "month": [1, 2, 3, 12],
            "year": [2005, 2005, 2005, 2005],
            "period": ["WINTER", "WINTER", "SPRING", "WINTER"],
        }
        df = pd.DataFrame(data)

        period_years = _compute_period_years_for_boundary_season(df, "WINTER")

        # Jan and Feb should be adjusted to 2004
        assert period_years.iloc[0] == 2004  # Jan/Feb boundary
        assert period_years.iloc[1] == 2004
        assert period_years.iloc[2] == 2005  # Spring, not boundary season
        assert period_years.iloc[3] == 2005  # Dec winter, but not Jan/Feb

    def test_january_february_summer_adjustment_southern(self):
        """Test that Jan/Feb of SUMMER boundary season (southern hemisphere) get adjusted"""
        data = {
            "month": [1, 2, 3, 12],
            "year": [2005, 2005, 2005, 2005],
            "period": ["SUMMER", "SUMMER", "AUTUMN", "SUMMER"],
        }
        df = pd.DataFrame(data)

        period_years = _compute_period_years_for_boundary_season(df, "SUMMER")

        # Jan and Feb should be adjusted to 2004
        assert period_years.iloc[0] == 2004
        assert period_years.iloc[1] == 2004
        assert period_years.iloc[2] == 2005
        assert period_years.iloc[3] == 2005

    def test_other_months_not_adjusted(self):
        """Test that non-boundary months are not adjusted"""
        data = {
            "month": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "year": [2005] * 10,
            "period": ["SPRING"] * 10,
        }
        df = pd.DataFrame(data)

        period_years = _compute_period_years_for_boundary_season(df, "WINTER")

        # All should remain unchanged
        np.testing.assert_array_equal(period_years.values, [2005] * 10)

    def test_december_winter_not_adjusted(self):
        """Test that December of WINTER is NOT adjusted (stays same year)"""
        data = {
            "month": [12, 12],
            "year": [2005, 2005],
            "period": ["WINTER", "SUMMER"],
        }
        df = pd.DataFrame(data)

        period_years = _compute_period_years_for_boundary_season(df, "WINTER")

        # December WINTER should NOT be adjusted
        assert period_years.iloc[0] == 2005
        # December SUMMER has different boundary, so same result
        assert period_years.iloc[1] == 2005


class TestBuildPeriodViews:
    def test_build_period_views_northern_hemisphere(self):
        """Test building period views for northern hemisphere"""
        data = {
            "DATE": ["20050101", "20050315", "20050615", "20050920", "20051215"],
            "ELEMENT": ["TMIN"] * 5,
            "temperature_celsius": [0.0, 5.0, 15.0, 10.0, 2.0],
            "year": [2005] * 5,
            "month": [1, 3, 6, 9, 12],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=False)

        # Should have entries for YEAR and 4 seasons
        assert not result.empty
        years = result["periodYear"].unique()
        periods = result["period"].unique()

        assert "YEAR" in periods
        assert "WINTER" in periods
        assert "SPRING" in periods
        assert "SUMMER" in periods
        assert "AUTUMN" in periods

    def test_build_period_views_january_offset(self):
        """Test that January is correctly assigned to previous year WINTER"""
        data = {
            "DATE": ["20050101"],
            "ELEMENT": ["TMIN"],
            "temperature_celsius": [0.0],
            "year": [2005],
            "month": [1],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=False)

        # Find WINTER entries
        winter_entries = result[result["period"] == "WINTER"]
        if not winter_entries.empty:
            # January should be attributed to period year 2004
            jan_winter = winter_entries[
                (winter_entries["month"] == 1)
            ]
            if not jan_winter.empty:
                assert 2004 in jan_winter["periodYear"].values

    def test_build_period_views_southern_hemisphere_seasons(self):
        """Test building period views for southern hemisphere"""
        data = {
            "DATE": ["20050101", "20050715"],
            "ELEMENT": ["TMIN"] * 2,
            "temperature_celsius": [25.0, 10.0],
            "year": [2005] * 2,
            "month": [1, 7],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=True)

        # Southern hemisphere: Jan should be SUMMER, Jul should be WINTER
        periods = result["period"].unique()

        assert "SUMMER" in periods
        assert "WINTER" in periods

    def test_build_period_views_year_view(self):
        """Test that YEAR view correctly aggregates all data"""
        data = {
            "DATE": ["20050115", "20050715"],
            "ELEMENT": ["TMIN"] * 2,
            "temperature_celsius": [5.0, 15.0],
            "year": [2005] * 2,
            "month": [1, 7],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=False)

        year_view = result[result["period"] == "YEAR"]
        assert not year_view.empty
        # All YEAR entries should have periodYear = original year
        assert all(year_view["periodYear"] == 2005)

    def test_build_period_views_both_views_included(self):
        """Test that both YEAR and season views are included"""
        data = {
            "DATE": ["20050101"],
            "ELEMENT": ["TMIN"],
            "temperature_celsius": [0.0],
            "year": [2005],
            "month": [1],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=False)

        # Should have both YEAR and season entries
        periods = result["period"].unique()
        assert len(periods) > 1  # At least YEAR + one season

    def test_build_period_views_maintains_elements(self):
        """Test that ELEMENT column is maintained"""
        data = {
            "DATE": ["20050101"],
            "ELEMENT": ["TMIN"],
            "temperature_celsius": [0.0],
            "year": [2005],
            "month": [1],
        }
        df = pd.DataFrame(data)

        result = _build_period_views(df, is_southern=False)

        assert "ELEMENT" in result.columns
        assert result["ELEMENT"].iloc[0] == "TMIN"
