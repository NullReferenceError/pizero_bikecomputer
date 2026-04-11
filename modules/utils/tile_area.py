"""
Tile area calculation utilities for offline map tile pre-downloading.

This module provides functions to calculate which map tiles are needed
for a given geographic area (radius from center point) at specific zoom levels.
Uses the same Web Mercator projection and tile calculation as the runtime app.
"""

import math
from typing import List, Tuple, Dict

from modules.utils.map import get_tilexy_and_xy_in_tile


# Earth radius in kilometers (mean radius)
EARTH_RADIUS_KM = 6371.0

# Average tile size in bytes (empirical values for PNG tiles)
# These are conservative estimates; actual sizes vary by zoom level and content
AVERAGE_TILE_SIZE_BYTES = {
    8: 15000,   # ~15 KB - low detail
    9: 18000,   # ~18 KB
    10: 20000,  # ~20 KB
    11: 20000,  # ~20 KB
    12: 20000,  # ~20 KB
    13: 22000,  # ~22 KB
    14: 25000,  # ~25 KB - more detail, larger files
    15: 28000,  # ~28 KB
    16: 32000,  # ~32 KB
    17: 35000,  # ~35 KB - maximum detail
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on Earth.
    
    Uses the Haversine formula for accurate distance calculation at any latitude.
    
    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees
    
    Returns:
        Distance in kilometers
    """
    # Convert to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = (math.sin(dlat / 2) ** 2 + 
         math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2)
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_KM * c


def get_bounding_box_from_radius(center_lat: float, center_lon: float, 
                                  radius_km: float) -> Tuple[float, float, float, float]:
    """
    Calculate a bounding box (rectangle) that contains a circular area.
    
    This is used as a first-pass filter to quickly eliminate tiles that are
    definitely outside the radius without expensive distance calculations.
    
    Args:
        center_lat: Center latitude in decimal degrees
        center_lon: Center longitude in decimal degrees
        radius_km: Radius in kilometers
    
    Returns:
        Tuple of (min_lat, max_lat, min_lon, max_lon)
    """
    # Calculate latitude offset (same at all longitudes)
    lat_offset = math.degrees(radius_km / EARTH_RADIUS_KM)
    
    # Calculate longitude offset (varies by latitude)
    # At higher latitudes, longitude degrees cover less distance
    lon_offset = math.degrees(
        radius_km / (EARTH_RADIUS_KM * math.cos(math.radians(center_lat)))
    )
    
    min_lat = max(center_lat - lat_offset, -85.0511)  # Web Mercator limit
    max_lat = min(center_lat + lat_offset, 85.0511)
    min_lon = center_lon - lon_offset
    max_lon = center_lon + lon_offset
    
    # Handle longitude wrapping
    if min_lon < -180:
        min_lon += 360
    if max_lon > 180:
        max_lon -= 360
    
    return min_lat, max_lat, min_lon, max_lon


def get_tile_center_latlng(tile_x: int, tile_y: int, zoom: int) -> Tuple[float, float]:
    """
    Get the center lat/lon of a tile.
    
    Args:
        tile_x: Tile X coordinate
        tile_y: Tile Y coordinate
        zoom: Zoom level
    
    Returns:
        Tuple of (latitude, longitude) in decimal degrees
    """
    n = 2.0 ** zoom
    
    # Center of tile (add 0.5 to get middle)
    lon = ((tile_x + 0.5) / n * 360.0) - 180.0
    
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 0.5) / n)))
    lat = math.degrees(lat_rad)
    
    return lat, lon


def get_tiles_in_radius(center_lat: float, center_lon: float, 
                        radius_km: float, zoom: int,
                        tile_size: int = 256) -> List[Tuple[int, int]]:
    """
    Calculate all map tiles within a circular radius from a center point.
    
    This is the core function for determining which tiles to download.
    Uses a two-pass approach:
    1. Calculate bounding box and get all tiles in that rectangle (fast)
    2. Filter by actual distance to tile center (accurate)
    
    Args:
        center_lat: Center latitude in decimal degrees (-90 to +90)
        center_lon: Center longitude in decimal degrees (-180 to +180)
        radius_km: Radius in kilometers
        zoom: Zoom level (typically 8-17 for cycling)
        tile_size: Tile size in pixels (default: 256)
    
    Returns:
        Sorted list of (tile_x, tile_y) tuples
    """
    # Step 1: Get bounding box
    min_lat, max_lat, min_lon, max_lon = get_bounding_box_from_radius(
        center_lat, center_lon, radius_km
    )
    
    # Step 2: Convert corners to tile coordinates
    # Use the existing get_tilexy_and_xy_in_tile function for consistency
    min_tile_x, min_tile_y, _, _ = get_tilexy_and_xy_in_tile(
        zoom, min_lon, max_lat, tile_size
    )
    max_tile_x, max_tile_y, _, _ = get_tilexy_and_xy_in_tile(
        zoom, max_lon, min_lat, tile_size
    )
    
    # Ensure min <= max
    if min_tile_x > max_tile_x:
        min_tile_x, max_tile_x = max_tile_x, min_tile_x
    if min_tile_y > max_tile_y:
        min_tile_y, max_tile_y = max_tile_y, min_tile_y
    
    # Step 3: Generate all tiles in bounding box and filter by distance
    tiles = []
    for tile_x in range(min_tile_x, max_tile_x + 1):
        for tile_y in range(min_tile_y, max_tile_y + 1):
            # Get tile center
            tile_lat, tile_lon = get_tile_center_latlng(tile_x, tile_y, zoom)
            
            # Calculate distance from center to tile center
            distance = haversine_distance(
                center_lat, center_lon, tile_lat, tile_lon
            )
            
            # Include tile if its center is within radius
            # Add small buffer (1.5x diagonal tile size) to ensure coverage at edges
            tile_diagonal_km = (math.sqrt(2) * radius_km) / (2 ** zoom) * 0.01
            if distance <= radius_km + tile_diagonal_km:
                tiles.append((tile_x, tile_y))
    
    # Sort for consistent ordering (helpful for progress tracking)
    tiles.sort()
    return tiles


def estimate_tile_count_and_size(center_lat: float, center_lon: float,
                                  radius_km: float, 
                                  zoom_range: Tuple[int, int]) -> Dict[int, Dict[str, float]]:
    """
    Estimate the number of tiles and storage space needed for a download.
    
    This function is useful for showing users what they're about to download
    before actually starting the download process.
    
    Args:
        center_lat: Center latitude in decimal degrees
        center_lon: Center longitude in decimal degrees
        radius_km: Radius in kilometers
        zoom_range: Tuple of (min_zoom, max_zoom) inclusive
    
    Returns:
        Dictionary with zoom levels as keys, each containing:
        - 'count': Number of tiles
        - 'size_bytes': Estimated storage in bytes
        - 'size_mb': Estimated storage in megabytes
    
    Example:
        {
            12: {'count': 1234, 'size_bytes': 24680000, 'size_mb': 24.68},
            13: {'count': 4936, 'size_bytes': 98720000, 'size_mb': 98.72},
            ...
        }
    """
    min_zoom, max_zoom = zoom_range
    estimates = {}
    
    for zoom in range(min_zoom, max_zoom + 1):
        tiles = get_tiles_in_radius(center_lat, center_lon, radius_km, zoom)
        tile_count = len(tiles)
        
        # Get average tile size for this zoom level
        avg_size = AVERAGE_TILE_SIZE_BYTES.get(zoom, 25000)  # Default 25KB
        
        size_bytes = tile_count * avg_size
        size_mb = size_bytes / (1024 * 1024)
        
        estimates[zoom] = {
            'count': tile_count,
            'size_bytes': size_bytes,
            'size_mb': size_mb,
        }
    
    return estimates


def format_size(size_bytes: float) -> str:
    """
    Format bytes into human-readable string.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.5 GB", "234.5 MB", "45.2 KB")
    """
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.1f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes:.0f} bytes"


def get_tile_bounds_latlng(tile_x: int, tile_y: int, zoom: int) -> Dict[str, float]:
    """
    Get the lat/lon bounds of a tile (for debugging/visualization).
    
    Args:
        tile_x: Tile X coordinate
        tile_y: Tile Y coordinate
        zoom: Zoom level
    
    Returns:
        Dictionary with 'min_lat', 'max_lat', 'min_lon', 'max_lon'
    """
    n = 2.0 ** zoom
    
    # Northwest corner (top-left)
    nw_lon = (tile_x / n * 360.0) - 180.0
    nw_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * tile_y / n)))
    nw_lat = math.degrees(nw_lat_rad)
    
    # Southeast corner (bottom-right)
    se_lon = ((tile_x + 1) / n * 360.0) - 180.0
    se_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (tile_y + 1) / n)))
    se_lat = math.degrees(se_lat_rad)
    
    return {
        'min_lat': se_lat,
        'max_lat': nw_lat,
        'min_lon': nw_lon,
        'max_lon': se_lon,
    }


def miles_to_km(miles: float) -> float:
    """Convert miles to kilometers."""
    return miles * 1.60934


def km_to_miles(km: float) -> float:
    """Convert kilometers to miles."""
    return km / 1.60934
