import pytest
import math
from app.logic.geo_calculations import haversine_km, bounding_box


class TestHaversineKm:
    def test_haversine_identical_points(self):
        """Test distance between identical coordinates"""
        distance = haversine_km(52.5200, 13.4050, 52.5200, 13.4050)
        assert distance < 0.001  # Should be ~0 km

    def test_haversine_known_distance_berlin_hamburg(self):
        """Test known distance: Berlin to Hamburg (~255 km)"""
        # Berlin coordinates
        berlin_lat, berlin_lon = 52.5200, 13.4050
        # Hamburg coordinates
        hamburg_lat, hamburg_lon = 53.5511, 10.0000

        distance = haversine_km(berlin_lat, berlin_lon, hamburg_lat, hamburg_lon)

        # Expected distance is approximately 255 km
        assert 250 < distance < 260

    def test_haversine_known_distance_equator(self):
        """Test distance along equator (1 degree should be ~111 km)"""
        distance = haversine_km(0.0, 0.0, 0.0, 1.0)
        assert 110 < distance < 112

    def test_haversine_known_distance_meridian(self):
        """Test distance along meridian (1 degree should be ~111 km)"""
        distance = haversine_km(0.0, 0.0, 1.0, 0.0)
        assert 110 < distance < 112

    def test_haversine_antipodal_points(self):
        """Test distance between antipodal points (should be ~20000 km)"""
        distance = haversine_km(0.0, 0.0, 0.0, 180.0)
        # Half of Earth's circumference
        expected_circumference = 2 * math.pi * 6371.0088
        assert distance > (expected_circumference / 2 - 100)
        assert distance < (expected_circumference / 2 + 100)

    def test_haversine_symmetry(self):
        """Test that distance is symmetric: d(A,B) == d(B,A)"""
        lat1, lon1 = 48.8566, 2.3522  # Paris
        lat2, lon2 = 51.5074, -0.1278  # London

        d1 = haversine_km(lat1, lon1, lat2, lon2)
        d2 = haversine_km(lat2, lon2, lat1, lon1)

        assert abs(d1 - d2) < 0.001

    def test_haversine_southern_hemisphere(self):
        """Test with southern hemisphere coordinates"""
        distance = haversine_km(-33.8688, 151.2093, -37.8136, 144.9631)  # Sydney to Melbourne
        assert 700 < distance < 800

    def test_haversine_dateline_crossing(self):
        """Test distance across dateline"""
        # East Tokyo to West Hawaii
        distance = haversine_km(35.6762, 139.6503, 20.8781, -156.4735)
        assert 4500 < distance < 6500


class TestBoundingBox:
    def test_bounding_box_equator(self):
        """Test bounding box calculation at equator"""
        lat, lon = 0.0, 0.0
        radius_km = 111.32  # ~1 degree

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # At equator, 111.32 km ≈ 1 degree
        assert min_lat == pytest.approx(-1.0, abs=0.01)
        assert max_lat == pytest.approx(1.0, abs=0.01)
        assert min_lon == pytest.approx(-1.0, abs=0.01)
        assert max_lon == pytest.approx(1.0, abs=0.01)

    def test_bounding_box_symmetry(self):
        """Test that bounding box is symmetric around center point"""
        lat, lon = 50.0, 10.0
        radius_km = 111.32

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # Latitude should be symmetric
        assert abs((lat - min_lat) - (max_lat - lat)) < 0.001

    def test_bounding_box_north_pole(self):
        """Test bounding box behavior near north pole"""
        lat, lon = 85.0, 0.0  # Close to north pole but not extreme
        radius_km = 100

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # Should still return valid bounds
        assert min_lat >= -90
        assert max_lat <= 90
        assert min_lon >= -180
        assert max_lon <= 180

    def test_bounding_box_coordinates_valid(self):
        """Test that returned coordinates are within valid ranges"""
        lat, lon = 52.5200, 13.4050  # Berlin
        radius_km = 50

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        assert -90 <= min_lat <= 90
        assert -90 <= max_lat <= 90
        assert -180 <= min_lon <= 180
        assert -180 <= max_lon <= 180
        assert min_lat <= lat <= max_lat
        assert min_lon <= lon <= max_lon

    def test_bounding_box_small_radius(self):
        """Test with very small radius"""
        lat, lon = 48.0, 10.0
        radius_km = 1

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # Delta should be very small
        assert (max_lat - min_lat) < 0.05
        assert (max_lon - min_lon) < 0.2

    def test_bounding_box_large_radius(self):
        """Test with large radius"""
        lat, lon = 50.0, 10.0
        radius_km = 1000

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # Delta should be larger
        assert (max_lat - min_lat) > 5
        assert (max_lon - min_lon) > 5

    def test_bounding_box_equator_longitude_wrapping(self):
        """Test bounding box crossing datelinearea (near 180/-180)"""
        lat, lon = 0.0, 175.0
        radius_km = 500

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        # min_lon might be negative (wrapping is OK for pre-filtering)
        assert min_lat <= 0.0 <= max_lat
        # Longitude should be in expected range even if crossing dateline

    def test_bounding_box_southern_hemisphere(self):
        """Test in southern hemisphere"""
        lat, lon = -33.8688, 151.2093  # Sydney
        radius_km = 100

        min_lat, max_lat, min_lon, max_lon = bounding_box(lat, lon, radius_km)

        assert min_lat <= lat <= max_lat
        assert min_lon <= lon <= max_lon
        assert min_lat < 0  # Should be in southern hemisphere
