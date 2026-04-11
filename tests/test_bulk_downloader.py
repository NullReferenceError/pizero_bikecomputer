"""
Unit tests for bulk_tile_downloader.py module.

Tests rate limiting, statistics tracking, and download logic.
"""

import unittest
import asyncio
import time
import tempfile
import shutil
from pathlib import Path

from modules.helper.bulk_tile_downloader import (
    RateLimiter,
    DownloadStatistics,
    BulkTileDownloader,
)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting functionality."""
    
    def test_rate_limiter_basics(self):
        """Test basic rate limiter functionality."""
        async def test():
            limiter = RateLimiter(requests_per_second=10.0)
            
            start = time.monotonic()
            
            # Acquire 5 tokens rapidly (should be instant since we start with tokens)
            for _ in range(5):
                await limiter.acquire(1)
            
            elapsed = time.monotonic() - start
            # Should be very fast (< 0.1 second) as we have initial tokens
            self.assertLess(elapsed, 0.1)
        
        asyncio.run(test())
    
    def test_rate_limiter_throttling(self):
        """Test that rate limiter actually throttles requests."""
        async def test():
            # Very slow rate: 2 requests per second
            limiter = RateLimiter(requests_per_second=2.0)
            
            start = time.monotonic()
            
            # Consume initial tokens plus one more (should wait)
            for _ in range(4):
                await limiter.acquire(1)
            
            elapsed = time.monotonic() - start
            # Should take at least 1 second (4 requests at 2/sec)
            self.assertGreater(elapsed, 0.8)
        
        asyncio.run(test())


class TestDownloadStatistics(unittest.TestCase):
    """Test statistics tracking."""
    
    def test_statistics_initialization(self):
        """Test statistics start with correct values."""
        stats = DownloadStatistics()
        
        self.assertEqual(stats.total_tiles, 0)
        self.assertEqual(stats.downloaded_tiles, 0)
        self.assertEqual(stats.skipped_tiles, 0)
        self.assertEqual(stats.failed_tiles, 0)
        self.assertEqual(stats.total_bytes, 0)
        self.assertIsNone(stats.start_time)
        self.assertIsNone(stats.end_time)
    
    def test_statistics_tracking(self):
        """Test that statistics track correctly."""
        stats = DownloadStatistics()
        stats.start(100)
        
        # Simulate some downloads
        stats.add_downloaded(20000)
        stats.add_downloaded(25000)
        stats.add_skipped()
        stats.add_failed()
        
        self.assertEqual(stats.total_tiles, 100)
        self.assertEqual(stats.downloaded_tiles, 2)
        self.assertEqual(stats.skipped_tiles, 1)
        self.assertEqual(stats.failed_tiles, 1)
        self.assertEqual(stats.total_bytes, 45000)
        self.assertEqual(stats.completed_tiles, 3)
    
    def test_statistics_speed_calculation(self):
        """Test speed calculations."""
        stats = DownloadStatistics()
        stats.start(10)
        
        # Simulate some time passing
        time.sleep(0.1)
        stats.add_downloaded(100000)  # 100 KB
        
        # Should have some speed
        self.assertGreater(stats.speed_mbps, 0)
        self.assertGreater(stats.tiles_per_second, 0)


class TestBulkTileDownloader(unittest.TestCase):
    """Test bulk tile downloader functionality."""
    
    def setUp(self):
        """Create temporary directory for test tiles."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = Path.cwd()
        # Change to temp dir so tiles are created there
        import os
        os.chdir(self.temp_dir)
    
    def tearDown(self):
        """Clean up temporary directory."""
        import os
        os.chdir(self.original_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_downloader_initialization(self):
        """Test downloader initializes correctly."""
        map_config = {
            'test_map': {
                'url': 'https://example.com/{z}/{x}/{y}.png',
                'tile_size': 256,
            }
        }
        
        downloader = BulkTileDownloader(
            map_config=map_config,
            map_name='test_map',
            rate_limit=2.0,
            parallel_downloads=4
        )
        
        self.assertEqual(downloader.map_name, 'test_map')
        self.assertEqual(downloader.parallel_downloads, 4)
        self.assertIsNotNone(downloader.rate_limiter)
        self.assertIsNotNone(downloader.stats)
    
    def test_should_download_tile_logic(self):
        """Test tile download decision logic."""
        map_config = {
            'test_map': {
                'url': 'https://example.com/{z}/{x}/{y}.png',
                'tile_size': 256,
            }
        }
        
        downloader = BulkTileDownloader(
            map_config=map_config,
            map_name='test_map'
        )
        
        # Non-existent file should be downloaded
        self.assertTrue(downloader._should_download_tile('/nonexistent/file.png'))
        
        # Create a test file
        test_file = Path(self.temp_dir) / 'test_tile.png'
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_bytes(b'fake tile data')
        
        # Existing file should not be downloaded (unless force/update)
        self.assertFalse(downloader._should_download_tile(str(test_file)))
        
        # But should be downloaded if update_days is recent
        self.assertTrue(downloader._should_download_tile(str(test_file), update_days=0))
        
        # Create 0-byte file (404 marker)
        zero_file = Path(self.temp_dir) / 'zero_tile.png'
        zero_file.write_bytes(b'')
        
        # 0-byte files should not be re-downloaded
        self.assertFalse(downloader._should_download_tile(str(zero_file)))
    
    def test_get_tile_filename(self):
        """Test tile filename generation."""
        map_config = {
            'test_map': {
                'url': 'https://example.com/{z}/{x}/{y}.png',
                'tile_size': 256,
                'ext': 'png',
            }
        }
        
        downloader = BulkTileDownloader(
            map_config=map_config,
            map_name='test_map'
        )
        
        filename = downloader._get_tile_filename(100, 200, 15)
        
        # Should contain map name, zoom, and coordinates
        self.assertIn('test_map', filename)
        self.assertIn('15', filename)
        self.assertIn('100', filename)
        self.assertIn('200', filename)
        self.assertTrue(filename.endswith('.png'))


if __name__ == '__main__':
    unittest.main()
