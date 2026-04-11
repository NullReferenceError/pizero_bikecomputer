#!/usr/bin/env python3
"""
Offline Map Tile Downloader for Pi Zero Bikecomputer

This script pre-downloads map tiles for offline use, enabling navigation
in areas without cellular coverage. Downloads tiles within a circular radius
from a center point at specified zoom levels.

Usage:
    python scripts/download_map_tiles.py \\
        --center 40.7128,-74.0060 \\
        --radius 50 \\
        --zoom-range 12-15

For help:
    python scripts/download_map_tiles.py --help
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path
from typing import Tuple

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.utils.tile_area import (
    get_tiles_in_radius,
    estimate_tile_count_and_size,
    format_size,
    miles_to_km,
)
from modules.helper.bulk_tile_downloader import BulkTileDownloader
from modules.map_config import add_map_config


# Color codes for terminal output (if supported)
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def supports_color():
    """Check if terminal supports color output."""
    return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()


def colored(text: str, color: str) -> str:
    """Return colored text if terminal supports it."""
    if supports_color():
        return f"{color}{text}{Colors.ENDC}"
    return text


def parse_center(center_str: str) -> Tuple[float, float]:
    """
    Parse center coordinate string.
    
    Args:
        center_str: Comma-separated "lat,lon" string
    
    Returns:
        Tuple of (latitude, longitude)
    
    Raises:
        ValueError: If format is invalid
    """
    try:
        parts = center_str.split(',')
        if len(parts) != 2:
            raise ValueError("Center must be in format: lat,lon")
        
        lat = float(parts[0].strip())
        lon = float(parts[1].strip())
        
        # Validate ranges
        if not -90 <= lat <= 90:
            raise ValueError(f"Latitude must be between -90 and 90 (got {lat})")
        if not -180 <= lon <= 180:
            raise ValueError(f"Longitude must be between -180 and 180 (got {lon})")
        
        return lat, lon
    except ValueError as e:
        raise ValueError(f"Invalid center coordinates: {e}")


def parse_zoom_range(zoom_str: str) -> Tuple[int, int]:
    """
    Parse zoom range string.
    
    Args:
        zoom_str: Hyphen-separated "min-max" string (e.g., "12-15")
    
    Returns:
        Tuple of (min_zoom, max_zoom)
    
    Raises:
        ValueError: If format is invalid
    """
    try:
        parts = zoom_str.split('-')
        if len(parts) != 2:
            raise ValueError("Zoom range must be in format: min-max")
        
        min_zoom = int(parts[0].strip())
        max_zoom = int(parts[1].strip())
        
        # Validate ranges
        if not 0 <= min_zoom <= 20:
            raise ValueError(f"Min zoom must be between 0 and 20 (got {min_zoom})")
        if not 0 <= max_zoom <= 20:
            raise ValueError(f"Max zoom must be between 0 and 20 (got {max_zoom})")
        if min_zoom > max_zoom:
            raise ValueError(f"Min zoom ({min_zoom}) must be <= max zoom ({max_zoom})")
        
        return min_zoom, max_zoom
    except ValueError as e:
        raise ValueError(f"Invalid zoom range: {e}")


def format_coordinate(lat: float, lon: float) -> str:
    """Format coordinates in human-readable form with N/S/E/W."""
    lat_dir = 'N' if lat >= 0 else 'S'
    lon_dir = 'E' if lon >= 0 else 'W'
    return f"{abs(lat):.4f}°{lat_dir}, {abs(lon):.4f}°{lon_dir}"


def print_estimate(center_lat: float, center_lon: float, radius_km: float,
                   zoom_range: Tuple[int, int], map_name: str):
    """
    Print storage estimate and get user confirmation.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_km: Radius in kilometers
        zoom_range: (min_zoom, max_zoom) tuple
        map_name: Map source name
    """
    print()
    print(colored("═" * 70, Colors.HEADER))
    print(colored("  Map Tile Download Estimator", Colors.HEADER + Colors.BOLD))
    print(colored("═" * 70, Colors.HEADER))
    print()
    
    print(f"  Center: {format_coordinate(center_lat, center_lon)}")
    print(f"  Radius: {radius_km:.1f} km")
    print(f"  Map source: {colored(map_name, Colors.OKBLUE)}")
    print(f"  Zoom levels: {zoom_range[0]}-{zoom_range[1]}")
    print()
    
    # Calculate estimates
    estimates = estimate_tile_count_and_size(
        center_lat, center_lon, radius_km, zoom_range
    )
    
    print("  Storage Estimate:")
    print("  " + colored("─" * 66, Colors.OKCYAN))
    
    total_tiles = 0
    total_bytes = 0
    
    for zoom in sorted(estimates.keys()):
        est = estimates[zoom]
        total_tiles += est['count']
        total_bytes += est['size_bytes']
        
        tile_count_str = f"{est['count']:,}".rjust(10)
        size_str = format_size(est['size_bytes']).rjust(12)
        
        print(f"  Zoom {zoom:2d}: {tile_count_str} tiles  ×  ~20 KB  = {size_str}")
    
    print("  " + colored("─" * 66, Colors.OKCYAN))
    total_tiles_str = f"{total_tiles:,}".rjust(10)
    total_size_str = format_size(total_bytes).rjust(12)
    print(f"  {colored('TOTAL:', Colors.BOLD)}{total_tiles_str} tiles             {total_size_str}")
    print()
    
    # Warnings for large downloads
    if total_bytes > 1 * 1024 ** 3:  # > 1 GB
        gb_size = total_bytes / (1024 ** 3)
        print(colored(f"  ⚠ WARNING: This will download {gb_size:.1f} GB of data", Colors.WARNING))
    
    # Estimate download time (assume 1 MB/s average)
    est_time_seconds = total_bytes / (1024 * 1024)
    if est_time_seconds > 60:
        est_time_minutes = est_time_seconds / 60
        print(colored(f"  ⚠ Estimated time: ~{est_time_minutes:.0f} minutes at 1 MB/s", Colors.WARNING))
    
    print()


def print_progress_bar(current: int, total: int, speed_mbps: float, width: int = 50):
    """
    Print a progress bar for downloads.
    
    Args:
        current: Current number of tiles processed
        total: Total tiles to process
        speed_mbps: Download speed in MB/s
        width: Width of progress bar in characters
    """
    if total == 0:
        return
    
    percent = current / total
    filled = int(width * percent)
    bar = '█' * filled + '░' * (width - filled)
    
    percent_str = f"{percent * 100:5.1f}%"
    count_str = f"{current:,}/{total:,}".rjust(20)
    speed_str = f"{speed_mbps:.2f} MB/s"
    
    # Use \r to overwrite the same line
    print(f"\r  [{bar}] {percent_str} {count_str} tiles  {speed_str}", end='', flush=True)


class ProgressTracker:
    """Track and display download progress."""
    
    def __init__(self, zoom: int, quiet: bool = False):
        self.zoom = zoom
        self.quiet = quiet
        self.last_update = 0
    
    def __call__(self, current: int, total: int, speed_mbps: float):
        """Progress callback function."""
        if self.quiet:
            return
        
        # Update every 0.5 seconds to avoid too much output
        import time
        now = time.time()
        if now - self.last_update < 0.5 and current < total:
            return
        
        self.last_update = now
        print_progress_bar(current, total, speed_mbps)


def print_summary(results: dict):
    """
    Print download summary statistics.
    
    Args:
        results: Dictionary with download statistics
    """
    print()
    print()
    print(colored("═" * 70, Colors.OKGREEN))
    print(colored("  Download Complete!", Colors.OKGREEN + Colors.BOLD))
    print(colored("═" * 70, Colors.OKGREEN))
    print()
    
    total = results.get('total', 0)
    downloaded = results.get('downloaded', 0)
    skipped = results.get('skipped', 0)
    failed = results.get('failed', 0)
    
    success_rate = (downloaded / (downloaded + failed) * 100) if (downloaded + failed) > 0 else 100
    
    print(f"  Total tiles: {colored(f'{total:,}', Colors.BOLD)}")
    print(f"  Successfully downloaded: {colored(f'{downloaded:,}', Colors.OKGREEN)} ({success_rate:.1f}%)")
    if skipped > 0:
        print(f"  Already cached: {skipped:,}")
    if failed > 0:
        print(f"  Failed: {colored(f'{failed:,}', Colors.FAIL)}")
    print()
    
    total_mb = results.get('total_bytes', 0) / (1024 * 1024)
    elapsed = results.get('elapsed_time', 0)
    speed = results.get('speed_mbps', 0)
    
    print(f"  Total size: {format_size(results.get('total_bytes', 0))}")
    if elapsed > 60:
        elapsed_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"
    else:
        elapsed_str = f"{elapsed:.1f}s"
    print(f"  Download time: {elapsed_str}")
    print(f"  Average speed: {speed:.2f} MB/s")
    print()


async def download_tiles_for_area(
    center_lat: float,
    center_lon: float,
    radius_km: float,
    zoom_range: Tuple[int, int],
    map_config: dict,
    map_name: str,
    update_days: int = None,
    force: bool = False,
    parallel: int = 4,
    quiet: bool = False
):
    """
    Download tiles for an area.
    
    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius_km: Radius in kilometers
        zoom_range: (min_zoom, max_zoom) tuple
        map_config: Map configuration dictionary
        map_name: Map source name
        update_days: Re-download tiles older than N days
        force: Force re-download all tiles
        parallel: Number of parallel downloads
        quiet: Suppress progress output
    """
    # Determine rate limit (use 2 req/sec as safe default for OSM)
    rate_limit = 2.0
    
    # Create downloader
    downloader = BulkTileDownloader(
        map_config=map_config,
        map_name=map_name,
        rate_limit=rate_limit,
        parallel_downloads=parallel
    )
    
    # Download tiles for each zoom level
    for zoom in range(zoom_range[0], zoom_range[1] + 1):
        if not quiet:
            print()
            print(colored(f"Downloading tiles for zoom level {zoom}...", Colors.OKCYAN))
        
        # Calculate tiles for this zoom level
        tiles = get_tiles_in_radius(center_lat, center_lon, radius_km, zoom)
        
        # Set up progress tracker
        progress_callback = ProgressTracker(zoom, quiet)
        
        # Download tiles
        results = await downloader.download_tiles(
            tiles,
            zoom,
            update_days=update_days,
            force=force,
            progress_callback=progress_callback
        )
        
        if not quiet:
            print()  # New line after progress bar
            print(colored("  ✓ Complete", Colors.OKGREEN))
        
        # Reset statistics for next zoom level
        downloader.reset_statistics()
    
    return results


def main():
    """Main entry point for CLI script."""
    parser = argparse.ArgumentParser(
        description="Download map tiles for offline use in Pi Zero Bikecomputer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download 50-mile radius around New York City, zoom 12-15
  %(prog)s --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15

  # Update tiles older than 90 days
  %(prog)s --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15 --update 90

  # Show estimate without downloading
  %(prog)s --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15 --dry-run

  # Use kilometers instead of miles
  %(prog)s --center 35.6762,139.6503 --radius 80 --zoom-range 12-15 --radius-unit km
        """
    )
    
    # Required arguments
    parser.add_argument(
        '--center',
        required=True,
        metavar='LAT,LON',
        help='Center point coordinates in decimal degrees (e.g., 40.7128,-74.0060)'
    )
    parser.add_argument(
        '--radius',
        required=True,
        type=float,
        metavar='NUM',
        help='Radius from center point'
    )
    parser.add_argument(
        '--zoom-range',
        required=True,
        metavar='MIN-MAX',
        help='Zoom level range (e.g., 12-15 for cycling detail)'
    )
    
    # Optional arguments
    parser.add_argument(
        '--radius-unit',
        choices=['km', 'miles'],
        default='miles',
        help='Unit for radius (default: miles)'
    )
    parser.add_argument(
        '--map',
        dest='map_name',
        default='openstreetmap',
        help='Map source name (default: openstreetmap)'
    )
    parser.add_argument(
        '--output',
        default='maptile',
        help='Output directory (default: maptile/)'
    )
    parser.add_argument(
        '--parallel',
        type=int,
        default=4,
        help='Number of concurrent downloads (default: 4)'
    )
    parser.add_argument(
        '--update',
        type=int,
        metavar='DAYS',
        help='Re-download tiles older than N days'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force re-download all tiles regardless of age'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show estimate without downloading'
    )
    parser.add_argument(
        '--estimate-only',
        action='store_true',
        help='Show storage estimate and exit'
    )
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Minimal output (no progress bars)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Detailed logging output'
    )
    
    args = parser.parse_args()
    
    # Parse coordinates
    try:
        center_lat, center_lon = parse_center(args.center)
    except ValueError as e:
        print(colored(f"Error: {e}", Colors.FAIL), file=sys.stderr)
        sys.exit(1)
    
    # Parse zoom range
    try:
        zoom_range = parse_zoom_range(args.zoom_range)
    except ValueError as e:
        print(colored(f"Error: {e}", Colors.FAIL), file=sys.stderr)
        sys.exit(1)
    
    # Convert radius to km
    radius_km = args.radius if args.radius_unit == 'km' else miles_to_km(args.radius)
    
    # Change to output directory
    if args.output != 'maptile':
        os.makedirs(args.output, exist_ok=True)
        os.chdir(args.output)
    
    # Set up map configuration
    # Create a minimal config object
    class SimpleConfig:
        def __init__(self):
            self.G_MAP_CONFIG = {}
            self.G_HEATMAP_OVERLAY_MAP_CONFIG = {}
            self.G_RAIN_OVERLAY_MAP_CONFIG = {}
            self.G_WIND_OVERLAY_MAP_CONFIG = {}
            self.G_DEM_MAP_CONFIG = {}
    
    config = SimpleConfig()
    add_map_config(config)
    
    # Check if map exists
    if args.map_name not in config.G_MAP_CONFIG:
        print(colored(f"Error: Map '{args.map_name}' not found", Colors.FAIL), file=sys.stderr)
        print(f"Available maps: {', '.join(config.G_MAP_CONFIG.keys())}", file=sys.stderr)
        sys.exit(1)
    
    # Show estimate
    if not args.quiet:
        print_estimate(center_lat, center_lon, radius_km, zoom_range, args.map_name)
    
    # Exit if estimate-only or dry-run
    if args.estimate_only or args.dry_run:
        if args.dry_run:
            print(colored("  Dry run mode - no tiles downloaded", Colors.WARNING))
        sys.exit(0)
    
    # Confirm unless quiet
    if not args.quiet and not args.force:
        try:
            response = input(colored("  Continue? [y/N]: ", Colors.BOLD))
            if response.lower() != 'y':
                print("  Cancelled.")
                sys.exit(0)
        except KeyboardInterrupt:
            print("\n  Cancelled.")
            sys.exit(0)
    
    # Download tiles
    try:
        results = asyncio.run(download_tiles_for_area(
            center_lat=center_lat,
            center_lon=center_lon,
            radius_km=radius_km,
            zoom_range=zoom_range,
            map_config=config.G_MAP_CONFIG,
            map_name=args.map_name,
            update_days=args.update,
            force=args.force,
            parallel=args.parallel,
            quiet=args.quiet
        ))
        
        # Print summary
        if not args.quiet:
            print_summary(results)
            output_path = Path(args.output).resolve() / args.map_name
            print(f"  Tiles saved to: {colored(str(output_path), Colors.OKBLUE)}")
            print()
        
    except KeyboardInterrupt:
        print()
        print(colored("  Download interrupted by user", Colors.WARNING))
        sys.exit(1)
    except Exception as e:
        print()
        print(colored(f"  Error: {e}", Colors.FAIL), file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
