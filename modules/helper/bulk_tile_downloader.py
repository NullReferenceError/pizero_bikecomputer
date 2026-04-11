"""
Bulk tile downloader for offline map preparation.

This module orchestrates downloading large numbers of map tiles efficiently,
with rate limiting, progress tracking, and error handling. It reuses existing
HTTP download infrastructure while adding bulk download optimizations.
"""

import asyncio
import os
import time
from pathlib import Path
from typing import List, Tuple, Optional, Callable, Dict
from datetime import datetime

from modules.app_logger import app_logger
from modules.utils.map import get_maptile_filename
from modules.helper.network.http_client import download_files


class RateLimiter:
    """
    Token bucket rate limiter to respect tile server policies.
    
    Ensures we don't overwhelm tile servers with too many requests.
    Different map sources have different rate limits.
    """
    
    def __init__(self, requests_per_second: float = 2.0):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_second: Maximum requests allowed per second
        """
        self.rate = requests_per_second
        self.tokens = requests_per_second
        self.last_update = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1):
        """
        Wait until tokens are available, then consume them.
        
        Args:
            tokens: Number of tokens to acquire (usually 1 per tile)
        """
        async with self.lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_update
                
                # Refill tokens based on elapsed time
                self.tokens = min(
                    self.rate,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now
                
                # If we have enough tokens, consume and return
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Wait until we'd have enough tokens
                wait_time = (tokens - self.tokens) / self.rate
                await asyncio.sleep(wait_time)


class DownloadStatistics:
    """Track download progress and statistics."""
    
    def __init__(self):
        self.total_tiles = 0
        self.downloaded_tiles = 0
        self.skipped_tiles = 0  # Already exist
        self.failed_tiles = 0
        self.total_bytes = 0
        self.start_time = None
        self.end_time = None
    
    def start(self, total_tiles: int):
        """Start tracking for a download session."""
        self.total_tiles = total_tiles
        self.start_time = time.time()
    
    def finish(self):
        """Mark download session as finished."""
        self.end_time = time.time()
    
    def add_downloaded(self, size_bytes: int = 0):
        """Record a successful download."""
        self.downloaded_tiles += 1
        self.total_bytes += size_bytes
    
    def add_skipped(self):
        """Record a skipped tile (already exists)."""
        self.skipped_tiles += 1
    
    def add_failed(self):
        """Record a failed download."""
        self.failed_tiles += 1
    
    @property
    def completed_tiles(self) -> int:
        """Total tiles processed (downloaded + skipped)."""
        return self.downloaded_tiles + self.skipped_tiles
    
    @property
    def elapsed_time(self) -> float:
        """Time elapsed in seconds."""
        if not self.start_time:
            return 0
        end = self.end_time if self.end_time else time.time()
        return end - self.start_time
    
    @property
    def speed_mbps(self) -> float:
        """Download speed in MB/s."""
        if self.elapsed_time == 0:
            return 0
        return (self.total_bytes / (1024 * 1024)) / self.elapsed_time
    
    @property
    def tiles_per_second(self) -> float:
        """Tiles downloaded per second."""
        if self.elapsed_time == 0:
            return 0
        return self.downloaded_tiles / self.elapsed_time


class BulkTileDownloader:
    """
    Orchestrates bulk tile downloads for offline map usage.
    
    Features:
    - Rate limiting per map source
    - Progress tracking with callbacks
    - Skip existing tiles (or update old ones)
    - Batch downloading with controlled concurrency
    - Error handling and retry logic
    - Statistics tracking
    """
    
    def __init__(self, map_config: dict, map_name: str,
                 rate_limit: float = 2.0,
                 parallel_downloads: int = 4):
        """
        Initialize bulk downloader.
        
        Args:
            map_config: Map configuration dictionary (from config.G_MAP_CONFIG)
            map_name: Name of map source (e.g., 'openstreetmap')
            rate_limit: Maximum requests per second (default: 2.0)
            parallel_downloads: Number of concurrent downloads (default: 4)
        """
        self.map_config = map_config
        self.map_name = map_name
        self.map_settings = map_config[map_name]
        self.rate_limiter = RateLimiter(rate_limit)
        self.parallel_downloads = parallel_downloads
        self.stats = DownloadStatistics()
    
    def _get_tile_filename(self, tile_x: int, tile_y: int, zoom: int) -> str:
        """
        Get the filename for a tile.
        
        Reuses existing get_maptile_filename for consistency.
        """
        return get_maptile_filename(
            self.map_name, zoom, tile_x, tile_y, self.map_settings
        )
    
    def _should_download_tile(self, filename: str, 
                              update_days: Optional[int] = None) -> bool:
        """
        Check if a tile needs to be downloaded.
        
        Args:
            filename: Path to tile file
            update_days: If set, re-download tiles older than N days
        
        Returns:
            True if tile should be downloaded, False if it can be skipped
        """
        # Check if file exists
        if not os.path.exists(filename):
            return True
        
        # Check file size (0-byte files are 404 markers, skip them)
        if os.path.getsize(filename) == 0:
            return False
        
        # If update_days not set, don't re-download existing tiles
        if update_days is None:
            return False
        
        # Check file age
        file_mtime = os.path.getmtime(filename)
        file_age_days = (time.time() - file_mtime) / (60 * 60 * 24)
        
        return file_age_days > update_days
    
    @staticmethod
    def _make_tile_directory(filename: str):
        """Create directory for a tile if it doesn't exist."""
        directory = os.path.dirname(filename)
        os.makedirs(directory, exist_ok=True)
    
    async def _download_batch(self, batch: List[Tuple[int, int, int]],
                              progress_callback: Optional[Callable] = None) -> int:
        """
        Download a batch of tiles.
        
        Args:
            batch: List of (tile_x, tile_y, zoom) tuples
            progress_callback: Optional callback for progress updates
        
        Returns:
            Number of successfully downloaded tiles
        """
        if not batch:
            return 0
        
        # Prepare URLs and save paths
        urls = []
        save_paths = []
        headers = {}
        
        # Set up headers if needed
        if self.map_settings.get("referer"):
            headers["Referer"] = self.map_settings["referer"]
        if self.map_settings.get("user_agent"):
            headers["User-Agent"] = "Pizero Bikecomputer (Offline Map Downloader)"
        
        # Build URL list
        for tile_x, tile_y, zoom in batch:
            url = self.map_settings["url"].format(z=zoom, x=tile_x, y=tile_y)
            filename = self._get_tile_filename(tile_x, tile_y, zoom)
            
            # Create directory if needed
            self._make_tile_directory(filename)
            
            urls.append(url)
            save_paths.append(filename)
        
        # Apply rate limiting
        await self.rate_limiter.acquire(len(batch))
        
        # Download files
        try:
            results = await download_files(
                urls=urls,
                headers=headers,
                save_paths=save_paths,
                limit=self.parallel_downloads
            )
            
            # Count successes and track statistics
            success_count = 0
            for result, save_path in zip(results, save_paths):
                if result == 200:  # HTTP OK
                    success_count += 1
                    # Get file size for statistics
                    try:
                        size = os.path.getsize(save_path)
                        self.stats.add_downloaded(size)
                    except:
                        self.stats.add_downloaded()
                elif result == 404:
                    # Create 0-byte marker file for 404s (existing behavior)
                    with open(save_path, 'w') as f:
                        pass
                    self.stats.add_failed()
                else:
                    self.stats.add_failed()
                    app_logger.warning(f"Failed to download tile {save_path}: HTTP {result}")
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(
                    self.stats.completed_tiles,
                    self.stats.total_tiles,
                    self.stats.speed_mbps
                )
            
            return success_count
            
        except Exception as e:
            app_logger.error(f"Error downloading batch: {e}")
            self.stats.failed_tiles += len(batch)
            return 0
    
    async def download_tiles(self, tiles: List[Tuple[int, int]], zoom: int,
                           update_days: Optional[int] = None,
                           force: bool = False,
                           progress_callback: Optional[Callable] = None) -> Dict:
        """
        Download a list of tiles at a specific zoom level.
        
        Args:
            tiles: List of (tile_x, tile_y) tuples
            zoom: Zoom level
            update_days: If set, re-download tiles older than N days
            force: If True, re-download all tiles regardless of age
            progress_callback: Optional callback(current, total, speed_mbps)
        
        Returns:
            Dictionary with download statistics:
            {
                'total': int,
                'downloaded': int,
                'skipped': int,
                'failed': int,
                'total_bytes': int,
                'elapsed_time': float,
                'speed_mbps': float
            }
        """
        # Filter tiles that need downloading
        tiles_to_download = []
        for tile_x, tile_y in tiles:
            filename = self._get_tile_filename(tile_x, tile_y, zoom)
            
            if force or self._should_download_tile(filename, update_days):
                tiles_to_download.append((tile_x, tile_y, zoom))
            else:
                self.stats.add_skipped()
        
        # Start tracking
        self.stats.start(len(tiles))
        
        app_logger.info(
            f"Zoom {zoom}: {len(tiles_to_download)} tiles to download, "
            f"{self.stats.skipped_tiles} already cached"
        )
        
        # Download in batches
        batch_size = 50  # Download 50 tiles at a time
        for i in range(0, len(tiles_to_download), batch_size):
            batch = tiles_to_download[i:i + batch_size]
            await self._download_batch(batch, progress_callback)
        
        # Finish tracking
        self.stats.finish()
        
        # Return statistics
        return {
            'total': self.stats.total_tiles,
            'downloaded': self.stats.downloaded_tiles,
            'skipped': self.stats.skipped_tiles,
            'failed': self.stats.failed_tiles,
            'total_bytes': self.stats.total_bytes,
            'elapsed_time': self.stats.elapsed_time,
            'speed_mbps': self.stats.speed_mbps,
            'tiles_per_second': self.stats.tiles_per_second,
        }
    
    def reset_statistics(self):
        """Reset statistics for a new download session."""
        self.stats = DownloadStatistics()
