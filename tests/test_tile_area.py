"""
Unit tests for tile_area.py module.

Tests tile calculation accuracy, distance calculations, and storage estimates.
"""

import unittest
import math
from modules.utils.tile_area import (
    haversine_distance,
    get_bounding_box_from_radius,
    get_tile_center_latlng,
    get_tiles_in_radius,
    estimate_tile_count_and_size,
    format_size,
    miles_to_km,
    km_to_miles,
)


class TestHaversineDistance(unittest.TestCase):
    """Test distance calculations using Haversine formula."""
    
    def test_same_point(self):
        """Distance from a point to itself should be 0."""
        dist = haversine_distance(40.7128, -74.0060, 40.7128, -74.0060)
        self.assertAlmostEqual(dist, 0.0, places=2)
    
    def test_known_distances(self):
        """Test with known city-to-city distances."""
        # New York to Los Angeles: ~3944 km
        nyc = (40.7128, -74.0060)
        la = (34.0522, -118.2437)
        dist = haversine_distance(*nyc, *la)
        self.assertAlmostEqual(dist, 3944, delta=50)  # Within 50km
        
        # London to Paris: ~344 km
        london = (51.5074, -0.1278)
        paris = (48.8566, 2.3522)
        dist = haversine_distance(*london, *paris)
        self.assertAlmostEqual(dist, 344, delta=10)
    
    def test_equator_distance(self):
        """Test distance calculation at equator."""
        # 1 degree longitude at equator ≈ 111 km
        dist = haversine_distance(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(dist, 111.2, delta=1)


class TestBoundingBox(unittest.TestCase):
    """Test bounding box calculations."""
    
    def test_bounding_box_symmetry(self):
        """Bounding box should be symmetric around center."""
        center_lat, center_lon = 40.7128, -74.0060
        radius_km = 50
        
        min_lat, max_lat, min_lon, max_lon = get_bounding_box_from_radius(
            center_lat, center_lon, radius_km
        )
        
        # Check symmetry (approximately, due to Earth's curvature)
        lat_diff = max_lat - center_lat
        self.assertAlmostEqual(lat_diff, center_lat - min_lat, places=2)
    
    def test_bounding_box_limits(self):
        """Bounding box should respect Web Mercator limits."""
        # Test near poles
        min_lat, max_lat, _, _ = get_bounding_box_from_radius(80.0, 0.0, 500)
        self.assertLessEqual(max_lat, 85.0511)
        self.assertGreaterEqual(min_lat, -85.0511)


class TestTileCalculations(unittest.TestCase):
    """Test tile coordinate calculations."""
    
    def test_tile_center(self):
        """Test tile center calculation."""
        # Tile 0,0 at zoom 0 should be centered near 0,0
        lat, lon = get_tile_center_latlng(0, 0, 0)
        self.assertAlmostEqual(lat, 0.0, delta=85)  # Single tile covers a lot
        self.assertAlmostEqual(lon, 0.0, delta=180)
    
    def test_tiles_in_radius_small_area(self):
        """Test tile calculation for small radius."""
        # Very small radius at high zoom should return few tiles
        tiles = get_tiles_in_radius(40.7128, -74.0060, 1, zoom=15)  # 1 km radius
        
        # Should have at least 1 tile, but not too many
        self.assertGreater(len(tiles), 0)
        self.assertLess(len(tiles), 50)
    
    def test_tiles_in_radius_larger_area(self):
        """Test that tile count increases with radius squared."""
        center_lat, center_lon = 40.7128, -74.0060
        zoom = 12
        
        tiles_10km = get_tiles_in_radius(center_lat, center_lon, 10, zoom)
        tiles_20km = get_tiles_in_radius(center_lat, center_lon, 20, zoom)
        
        # Doubling radius should roughly quadruple tiles (area relationship)
        # Allow some tolerance due to tile boundaries and buffer
        ratio = len(tiles_20km) / len(tiles_10km)
        self.assertGreater(ratio, 2.5)  # At least 2.5x
        self.assertLess(ratio, 6.5)     # But not more than 6.5x
    
    def test_tiles_in_radius_zoom_levels(self):
        """Test that higher zoom levels have more tiles."""
        center_lat, center_lon = 40.7128, -74.0060
        radius_km = 50
        
        tiles_z10 = get_tiles_in_radius(center_lat, center_lon, radius_km, 10)
        tiles_z11 = get_tiles_in_radius(center_lat, center_lon, radius_km, 11)
        tiles_z12 = get_tiles_in_radius(center_lat, center_lon, radius_km, 12)
        
        # Each zoom level should have ~4x more tiles
        self.assertGreater(len(tiles_z11), len(tiles_z10) * 3)
        self.assertGreater(len(tiles_z12), len(tiles_z11) * 3)
    
    def test_tiles_sorted(self):
        """Test that returned tiles are sorted."""
        tiles = get_tiles_in_radius(40.7128, -74.0060, 10, zoom=12)
        
        # Check if list is sorted
        self.assertEqual(tiles, sorted(tiles))
    
    def test_tiles_unique(self):
        """Test that no duplicate tiles are returned."""
        tiles = get_tiles_in_radius(40.7128, -74.0060, 50, zoom=12)
        
        # Check no duplicates
        self.assertEqual(len(tiles), len(set(tiles)))


class TestStorageEstimates(unittest.TestCase):
    """Test storage estimation functions."""
    
    def test_estimate_structure(self):
        """Test that estimate returns correct structure."""
        estimates = estimate_tile_count_and_size(
            40.7128, -74.0060, 50, (12, 14)
        )
        
        # Check all zoom levels present
        self.assertIn(12, estimates)
        self.assertIn(13, estimates)
        self.assertIn(14, estimates)
        
        # Check structure of each estimate
        for zoom, est in estimates.items():
            self.assertIn('count', est)
            self.assertIn('size_bytes', est)
            self.assertIn('size_mb', est)
            
            # Sanity checks
            self.assertGreater(est['count'], 0)
            self.assertGreater(est['size_bytes'], 0)
            self.assertGreater(est['size_mb'], 0)
    
    def test_estimate_size_scaling(self):
        """Test that storage estimates scale with tile count."""
        estimates = estimate_tile_count_and_size(
            40.7128, -74.0060, 50, (12, 13)
        )
        
        z12 = estimates[12]
        z13 = estimates[13]
        
        # Higher zoom should have more tiles and more storage
        self.assertGreater(z13['count'], z12['count'])
        self.assertGreater(z13['size_bytes'], z12['size_bytes'])


class TestFormatSize(unittest.TestCase):
    """Test human-readable size formatting."""
    
    def test_bytes(self):
        """Test formatting of small sizes."""
        self.assertEqual(format_size(500), "500 bytes")
    
    def test_kilobytes(self):
        """Test KB formatting."""
        self.assertEqual(format_size(1024), "1.0 KB")
        self.assertEqual(format_size(1536), "1.5 KB")
    
    def test_megabytes(self):
        """Test MB formatting."""
        self.assertEqual(format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(format_size(5.5 * 1024 * 1024), "5.5 MB")
    
    def test_gigabytes(self):
        """Test GB formatting."""
        self.assertEqual(format_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(format_size(2.75 * 1024 * 1024 * 1024), "2.8 GB")


class TestUnitConversions(unittest.TestCase):
    """Test unit conversion functions."""
    
    def test_miles_to_km(self):
        """Test miles to kilometers conversion."""
        self.assertAlmostEqual(miles_to_km(1), 1.60934, places=3)
        self.assertAlmostEqual(miles_to_km(50), 80.467, places=1)
        self.assertAlmostEqual(miles_to_km(100), 160.934, places=1)
    
    def test_km_to_miles(self):
        """Test kilometers to miles conversion."""
        self.assertAlmostEqual(km_to_miles(1.60934), 1, places=3)
        self.assertAlmostEqual(km_to_miles(100), 62.137, places=1)
    
    def test_conversion_roundtrip(self):
        """Test that conversions are reversible."""
        original = 50.0
        converted = miles_to_km(km_to_miles(original))
        self.assertAlmostEqual(converted, original, places=3)


if __name__ == '__main__':
    unittest.main()
