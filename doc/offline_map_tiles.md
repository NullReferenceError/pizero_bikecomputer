# Offline Map Tiles Guide

## Overview

The Pi Zero Bikecomputer can pre-download map tiles for offline use, enabling navigation in areas without cellular coverage. This guide explains how to use the offline map tile downloader to prepare map coverage before your rides.

## Benefits

- **Reliable Navigation**: No dependency on cellular/WiFi during rides
- **Faster Performance**: Instant map rendering without network delays
- **Reduced Bandwidth**: No data usage during rides (important for metered connections)
- **Remote Area Support**: Navigate confidently in areas with poor/no coverage

## Quick Start

### Basic Usage

Download tiles for a 50-mile radius around your home:

```bash
cd /path/to/pizero_bikecomputer

python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 \
  --radius 50 \
  --zoom-range 12-15
```

This will:
1. Show a storage estimate
2. Ask for confirmation
3. Download all tiles for zoom levels 12-15
4. Save tiles to `maptile/openstreetmap/` directory

### Finding Your Coordinates

**Method 1: From GPS on device**
Check the debug log for recent GPS coordinates:
```bash
grep "pos_lat\|pos_lon" log/debug.log | tail -2
```

**Method 2: From Google Maps**
1. Right-click on your desired location
2. Click the coordinates to copy them
3. Format as: `latitude,longitude` (e.g., `40.7128,-74.0060`)

**Method 3: From command line**
```bash
curl "https://nominatim.openstreetmap.org/search?q=New+York&format=json" | \
  python -c "import json,sys; d=json.load(sys.stdin)[0]; print(f\"{d['lat']},{d['lon']}\")"
```

## Understanding Zoom Levels

Different zoom levels provide different levels of detail:

| Zoom | Detail Level | What You See | Best For |
|------|--------------|--------------|----------|
| 10 | Region | Multiple cities, major roads | Long-distance overview |
| 11 | County | City outlines, highways | Regional planning |
| 12 | City | Neighborhoods, main streets | Urban navigation |
| 13 | Neighborhood | Street names, parks | Local riding |
| 14 | Street detail | All streets, bike paths | Turn-by-turn navigation |
| 15 | Maximum detail | Building-level, small paths | Detailed route finding |

### Recommended Zoom Ranges

**For Daily Local Riding (30 miles)**
```bash
--zoom-range 13-15
```
- High detail for street-level navigation
- ~300-500 MB storage

**For Weekend Tours (50-100 miles)**
```bash
--zoom-range 12-14
```
- Good balance of coverage and detail
- ~400-800 MB storage

**For Long-Distance Rides (100+ miles)**
```bash
--zoom-range 11-13
```
- Broader coverage, lower detail
- ~200-400 MB storage

**For Everything (Maximum Flexibility)**
```bash
--zoom-range 12-15
```
- Most common choice
- ~800 MB - 3 GB depending on radius

## Storage Requirements

### By Radius (Zoom 12-15)

| Radius | Approx Tiles | Storage | Download Time* |
|--------|--------------|---------|----------------|
| 10 miles | ~8,000 | ~170 MB | ~3 min |
| 20 miles | ~32,000 | ~650 MB | ~11 min |
| 30 miles | ~72,000 | ~1.5 GB | ~25 min |
| 40 miles | ~128,000 | ~2.6 GB | ~43 min |
| 50 miles | ~200,000 | ~4.0 GB | ~67 min |
| 75 miles | ~450,000 | ~9.0 GB | ~2.5 hrs |
| 100 miles | ~800,000 | ~16 GB | ~4.5 hrs |

*Assumes 1 MB/s connection speed

### By Zoom Level (50-mile radius)

| Zoom | Tiles | Storage | Tile Size at 256×256 pixels |
|------|-------|---------|------------------------------|
| 10 | ~300 | ~6 MB | City region coverage |
| 11 | ~1,200 | ~24 MB | County-level coverage |
| 12 | ~4,800 | ~96 MB | City overview |
| 13 | ~19,200 | ~384 MB | Neighborhood detail |
| 14 | ~76,800 | ~1.5 GB | Street detail |
| 15 | ~307,200 | ~6.1 GB | Maximum cycling detail |

**Total for z=12-15 @ 50mi:** ~8 GB

## Usage Examples

### Example 1: Preparing for a Local Ride

Download high-detail tiles for a 30-mile radius:

```bash
python scripts/download_map_tiles.py \
  --center 37.7749,-122.4194 \
  --radius 30 \
  --zoom-range 13-15
```

### Example 2: Planning a Long Tour

Download moderate-detail tiles for a 100-mile radius:

```bash
python scripts/download_map_tiles.py \
  --center 45.5231,-122.6765 \
  --radius 100 \
  --zoom-range 11-14
```

### Example 3: Using Kilometers

For users outside the US:

```bash
python scripts/download_map_tiles.py \
  --center 51.5074,-0.1278 \
  --radius 80 \
  --radius-unit km \
  --zoom-range 12-14
```

### Example 4: Updating Old Tiles

Refresh tiles older than 90 days (roads may have changed):

```bash
python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 \
  --radius 50 \
  --zoom-range 12-15 \
  --update 90
```

### Example 5: Dry Run (Estimate Only)

See what would be downloaded without actually downloading:

```bash
python scripts/download_map_tiles.py \
  --center 35.6762,139.6503 \
  --radius 50 \
  --zoom-range 12-15 \
  --dry-run
```

### Example 6: Desktop Download + Transfer

Download on a faster machine, then transfer to Pi Zero:

```bash
# On your laptop
python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 \
  --radius 50 \
  --zoom-range 12-15 \
  --output /tmp/bike_tiles/

# Transfer to Pi Zero via SSH
rsync -av --progress /tmp/bike_tiles/openstreetmap/ \
  pi@pizero.local:~/pizero_bikecomputer/maptile/openstreetmap/
```

### Example 7: Automation (Cron Job)

Schedule weekly tile updates:

```bash
# Add to crontab (run every Sunday at 2 AM)
crontab -e

# Add this line:
0 2 * * 0 cd /home/jack/pizero_bikecomputer && python scripts/download_map_tiles.py --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15 --update 90 --quiet >> log/tile_download.log 2>&1
```

## Command Reference

### Required Arguments

- `--center LAT,LON` - Center point in decimal degrees (e.g., `40.7128,-74.0060`)
- `--radius NUM` - Radius from center point
- `--zoom-range MIN-MAX` - Zoom levels to download (e.g., `12-15`)

### Optional Arguments

- `--radius-unit {km,miles}` - Unit for radius (default: `miles`)
- `--map NAME` - Map source name (default: `openstreetmap`)
- `--output PATH` - Output directory (default: `maptile/`)
- `--parallel N` - Concurrent downloads (default: `4`)
- `--update DAYS` - Re-download tiles older than N days
- `--force` - Force re-download all tiles
- `--dry-run` - Show estimate without downloading
- `--estimate-only` - Show storage estimate and exit
- `--quiet` - Minimal output (for scripting)
- `--verbose` - Detailed logging output

### Examples with Options

```bash
# High-speed download on desktop (8 parallel connections)
python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15 \
  --parallel 8

# Scripting mode (no progress bars, no prompts)
python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 --radius 50 --zoom-range 12-15 \
  --quiet --force

# Different map source
python scripts/download_map_tiles.py \
  --center 35.6762,139.6503 --radius 50 --zoom-range 12-15 \
  --map jpn_kokudo_chiri_in
```

## Tile Server Policies

When bulk downloading, it's important to respect tile server usage policies.

### OpenStreetMap (Default)

- **Policy**: https://operations.osmfoundation.org/policies/tiles/
- **Rate Limit**: Max 2 tiles/second (automatically enforced)
- **Bulk Downloads**: Acceptable for personal use
- **User-Agent**: Automatically set to "Pizero Bikecomputer"

**Best Practices**:
- Don't download excessively large areas at high zoom levels
- Use `--update` to refresh old tiles rather than re-downloading everything
- Consider downloading during off-peak hours for very large areas

### Other Map Sources

Each map source has specific policies configured in the system:

- **Wikimedia**: Similar to OSM, 2 req/sec
- **Japanese GSI Maps**: More permissive for bulk downloads
- **Commercial Sources**: May require API keys or subscriptions

The downloader automatically enforces appropriate rate limits per source.

## Tips for Pi Zero Users

### Storage Management

The Pi Zero typically uses an SD card (8-32 GB). Here's how to manage storage:

```bash
# Check available space
df -h ~/pizero_bikecomputer/maptile/

# Check size of downloaded maps
du -sh ~/pizero_bikecomputer/maptile/*

# Clear old maps you don't need
rm -rf ~/pizero_bikecomputer/maptile/old_map_name/

# Clear all cached weather/overlay tiles (if not needed)
rm -rf ~/pizero_bikecomputer/maptile/*/202*/
```

### Download Speed Optimization

**On Pi Zero (Slow WiFi)**:
- Use `--parallel 2` (default 4 may be too much)
- Download smaller areas or fewer zoom levels
- Consider downloading on desktop and transferring

**On Desktop/Laptop**:
- Use `--parallel 8` for faster downloads
- Transfer to Pi Zero via rsync
- Can prepare multiple areas at once

### Recommended SD Card Sizes

- **8 GB**: Basic setup, ~2-3 GB for maps (small area coverage)
- **16 GB**: Comfortable, ~5-8 GB for maps (moderate coverage)
- **32 GB**: Ideal, ~15-20 GB for maps (extensive coverage)
- **64 GB+**: Multiple map regions, all zoom levels

## How It Works

### Coordinate System

The downloader uses the same coordinate format as the bike computer's GPS:
- **Decimal degrees (WGS84)**: Standard GPS format
- Latitude range: -90 (South Pole) to +90 (North Pole)
- Longitude range: -180 (West) to +180 (East)
- Example: New York City = `40.7128,-74.0060`

### Tile Calculation

Tiles are calculated using **Web Mercator projection** (same as OpenStreetMap, Google Maps):

1. Convert center point and radius to a geographic bounding box
2. Calculate tile coordinates for bounding box corners at each zoom level
3. Filter tiles by actual distance (circular area, not rectangle)
4. Generate sorted list of tiles to download

At zoom level 15, one tile covers roughly:
- At equator: ~1.2 km × 1.2 km
- At 40° latitude: ~0.9 km × 1.2 km
- At 60° latitude: ~0.6 km × 1.2 km

### Download Process

1. **Estimate**: Calculate tiles needed and storage required
2. **Confirm**: Show summary and ask for user confirmation
3. **Filter**: Skip existing tiles (unless `--update` or `--force`)
4. **Download**: Batch download with rate limiting (50 tiles per batch)
5. **Verify**: Confirm successful downloads
6. **Repeat**: Process each zoom level sequentially

### Integration with Runtime App

Downloaded tiles are immediately usable:
- Stored in same format: `maptile/{map_name}/{z}/{x}/{y}.png`
- Same directory structure as on-demand downloads
- App automatically uses cached tiles (checks filesystem first)
- No configuration changes needed

## Troubleshooting

### "Insufficient disk space"

**Check available space**:
```bash
df -h ~/pizero_bikecomputer/maptile/
```

**Solutions**:
- Clear old map sources you don't use
- Use a narrower zoom range (e.g., `12-14` instead of `12-15`)
- Reduce radius
- Use a larger SD card

### "Rate limit exceeded" or slow downloads

**Cause**: Tile server is rate-limiting requests (429 error)

**Solutions**:
- Wait 60 seconds, the download will resume automatically
- Use `--parallel 2` for slower connections
- Download during off-peak hours
- Some servers may temporarily block after very large downloads

### "Connection timeout" or download failures

**Check network connectivity**:
```bash
ping tile.openstreetmap.org
```

**Solutions**:
- Check WiFi connection
- Try downloading smaller batches
- Use `--parallel 2` on Pi Zero
- Consider downloading on desktop and transferring

### Downloads are very slow on Pi Zero

**This is normal** - Pi Zero WiFi is limited to ~5-10 Mbps:
- Expected: 5-15 tiles per second
- Expected: 0.1-0.5 MB/s download speed

**Recommendations**:
- Download on desktop/laptop (10-50x faster)
- Transfer to Pi Zero via rsync or SD card reader
- Use `--parallel 2` to reduce memory pressure

### Tiles don't appear in the app

**Verify tiles were downloaded**:
```bash
ls -lh ~/pizero_bikecomputer/maptile/openstreetmap/15/29100/
```

**Check file permissions**:
```bash
chmod -R 755 ~/pizero_bikecomputer/maptile/
```

**Restart the app**:
```bash
sudo systemctl restart pizero_bikecomputer.service
```

**Check logs for errors**:
```bash
tail -f ~/pizero_bikecomputer/log/debug.log
```

### "Map 'X' not found" error

**List available maps**:
```bash
python scripts/download_map_tiles.py \
  --center 0,0 --radius 1 --zoom-range 10-10 2>&1 | \
  grep "Available maps"
```

**Default maps**:
- `openstreetmap` (default, worldwide)
- `wikimedia` (worldwide)
- `jpn_kokudo_chiri_in` (Japan only)

## Advanced Usage

### Multiple Areas

Download tiles for multiple locations:

```bash
# Home area (detailed)
python scripts/download_map_tiles.py \
  --center 40.7128,-74.0060 --radius 30 --zoom-range 13-15

# Vacation spot (moderate detail)
python scripts/download_map_tiles.py \
  --center 45.5231,-122.6765 --radius 60 --zoom-range 12-14

# Route corridor (lower detail for context)
python scripts/download_map_tiles.py \
  --center 42.3601,-71.0589 --radius 80 --zoom-range 11-13
```

### Different Map Types

Download multiple map types for the same area:

```bash
# Standard street map
python scripts/download_map_tiles.py \
  --center 35.6762,139.6503 --radius 50 --zoom-range 12-15 \
  --map openstreetmap

# Topographic map (if available)
python scripts/download_map_tiles.py \
  --center 35.6762,139.6503 --radius 50 --zoom-range 12-15 \
  --map jpn_kokudo_chiri_in
```

### Scripting Integration

Use in bash scripts:

```bash
#!/bin/bash
# Download tiles for upcoming ride locations

LOCATIONS=(
  "40.7128,-74.0060:New York"
  "37.7749,-122.4194:San Francisco"
  "41.8781,-87.6298:Chicago"
)

for loc in "${LOCATIONS[@]}"; do
  coords="${loc%:*}"
  name="${loc#*:}"
  
  echo "Downloading tiles for $name..."
  python scripts/download_map_tiles.py \
    --center "$coords" \
    --radius 40 \
    --zoom-range 12-14 \
    --quiet
done

echo "All downloads complete!"
```

## FAQs

**Q: How long does it take to download tiles?**  
A: Depends on area size, zoom levels, and connection speed:
- 50 mi @ z=12-15: 15-60 minutes (depending on machine)
- Pi Zero WiFi: ~1-2 hours
- Desktop fast connection: ~15-20 minutes

**Q: Can I download tiles for an entire state/country?**  
A: Not recommended. Even a small US state would be 100+ GB at high zoom levels. Instead:
- Download specific areas where you'll ride
- Use lower zoom levels (10-12) for large regions
- Focus on high zoom (13-15) for specific routes

**Q: Do I need to re-download tiles periodically?**  
A: Optional, but recommended for urban areas:
- Urban areas: Update every 3-6 months
- Rural areas: Once a year is fine
- Use `--update 90` to refresh tiles older than 90 days

**Q: Can I share tiles with other riders?**  
A: Yes! Tiles are just PNG images:
- Copy the `maptile/` folder to another device
- Use rsync to sync between devices
- Set up a local tile server for multiple bikes

**Q: Will navigation work completely offline?**  
A: Yes! Once tiles are downloaded:
- No internet connection needed during rides
- GPS works offline (satellite-based, not internet)
- Course following works offline
- Turn-by-turn navigation works offline

**Q: What if I ride outside my downloaded area?**  
A: The app will still work:
- If you have internet: Tiles download on-demand as before
- Without internet: Map shows blank areas outside coverage
- GPS tracking still works, just no map background

**Q: Can I delete tiles I don't need anymore?**  
A: Yes, safely delete entire map directories:
```bash
rm -rf ~/pizero_bikecomputer/maptile/old_area_name/
```

**Q: How do I know what area I've already downloaded?**  
A: Check the maptile directory:
```bash
# List downloaded map sources and zoom levels
ls ~/pizero_bikecomputer/maptile/
```

Each folder represents tiles for a specific map source. The app will use cached tiles automatically.

## See Also

- [GPS Setup Guide](gps_setup.md) - Configure GPS hardware
- [Map Configuration](../map.yaml) - Available map sources
- [Hardware Installation](hardware_installation.md) - Device setup

## Support

For issues or questions:
- Check `log/debug.log` for error messages
- Verify network connectivity and disk space
- Test with smaller area first (10 mile radius, z=12-13)
- Report issues on GitHub: https://github.com/hishizuka/pizero_bikecomputer/issues
