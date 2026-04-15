# Custom Scripts Best Practices

This guide explains how to safely create custom scripts for exporting and manipulating ride data from the pizero_bikecomputer system.

---

## ⚠️ Important Guidelines

### 1. File Naming Conventions

**ALWAYS use `.fit` extension for FIT file exports:**

```python
# ✅ GOOD: Proper .fit extension
output_file = "log/2026-04-14_16-38-37.fit"
```

```python
# ❌ BAD: Missing .fit extension
output_file = "log/ride_april14"  # Will trigger warning!
```

**Use proper timestamp format**: `YYYY-MM-DD_HH-MM-SS.fit`
- This matches the convention used by the normal reset workflow
- Makes files easy to sort and identify
- Example: `2026-04-14_16-38-37.fit` = April 14, 2026 at 4:38:37pm

---

### 2. Using the FIT Export API

The recommended way to export FIT files is to use the production `LoggerFit` class:

```python
#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/jack/pizero_bikecomputer')

from modules.logger.logger_fit import LoggerFit
from modules.logger.logger import Logger

# Create minimal config
db_path = '/home/jack/pizero_bikecomputer/log/log.db'
config = Logger.create_command_config(db_path)

# Initialize FIT logger
logger = LoggerFit(config)

# Get date range from database
start_date, end_date = logger.get_db_start_end_dates()

# Export with proper .fit extension
output_file = '/home/jack/pizero_bikecomputer/log/2026-04-14_16-38-37.fit'
success = logger.write_log(output_file, start_date, end_date)

if success:
    print(f"✓ Exported: {output_file}")
else:
    print(f"✗ Export failed")
```

---

### 3. Filtering Data by Date

The default `write_log()` exports **ALL** data from the database. To export a specific date range, create a filtered temporary database:

```python
import sqlite3
import tempfile

# Source database
original_db = '/home/jack/pizero_bikecomputer/log/log.db'

# Create temp database with filtered data
temp_db = tempfile.mktemp(suffix='.db')

con_orig = sqlite3.connect(original_db)
con_temp = sqlite3.connect(temp_db)

# Copy schema
schema = con_orig.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='BIKECOMPUTER_LOG'"
).fetchone()[0]
con_temp.execute(schema)

# Copy only records after specific timestamp
filter_start = '2026-04-14 22:00:00'  # 4pm MT = 22:00 UTC
cursor = con_orig.execute(
    "SELECT * FROM BIKECOMPUTER_LOG WHERE timestamp >= ?",
    (filter_start,)
)

# Get column names and insert
columns = [desc[0] for desc in cursor.description]
placeholders = ','.join(['?' for _ in columns])
insert_sql = f"INSERT INTO BIKECOMPUTER_LOG VALUES ({placeholders})"

records = cursor.fetchall()
con_temp.executemany(insert_sql, records)
con_temp.commit()

print(f"Filtered {len(records)} records")

con_orig.close()
con_temp.close()

# Now export the filtered database
config = Logger.create_command_config(temp_db)
logger = LoggerFit(config)
# ... continue with export ...

# Clean up temp database when done
os.remove(temp_db)
```

---

### 4. Avoiding setting.conf Corruption

The FIT export code automatically updates `setting.conf` with the uploaded file path. This is **intentional** behavior.

However, to avoid corruption:

✅ **DO:**
- Let the export code handle setting.conf updates
- Use absolute paths for output files
- Test your script thoroughly before using on real data

❌ **DON'T:**
- Manually edit setting.conf if possible
- Use relative paths that depend on current directory
- Run export scripts from random directories

If `setting.conf` gets corrupted (upload_file in wrong section), you can fix it by:
1. Backing up: `cp setting.conf setting.conf.backup`
2. Editing manually to move `upload_file` to `[GENERAL]` section
3. Or re-running a proper export script which will fix it automatically

---

### 5. Path Resolution

**ALWAYS use absolute paths** to avoid ambiguity:

```python
# ✅ GOOD: Absolute path
output_file = '/home/jack/pizero_bikecomputer/log/2026-04-14_16-38-37.fit'
```

```python
# ⚠️  RISKY: Relative path (depends on current directory)
output_file = 'log/2026-04-14_16-38-37.fit'
```

If you must use relative paths, ensure you're in the correct directory:

```python
import os
os.chdir('/home/jack/pizero_bikecomputer')
output_file = 'log/2026-04-14_16-38-37.fit'  # Now safe
```

---

### 6. Validation Warnings

As of April 14, 2026, the FIT export code validates filenames:

```python
# This will trigger a warning but still export:
logger.write_log('log/badfilename', start_date, end_date)

# Output: WARNING: FIT filename should end with .fit extension: log/badfilename
```

**Don't ignore these warnings!** They indicate potential issues that could cause upload failures.

---

## Common Use Cases

### Use Case 1: Export Last N Hours

```python
#!/usr/bin/env python3
"""Export only the last N hours of ride data"""
import sys
import sqlite3
from datetime import datetime, timedelta, timezone

sys.path.insert(0, '/home/jack/pizero_bikecomputer')

from modules.logger.logger_fit import LoggerFit
from modules.logger.logger import Logger

HOURS_AGO = 2  # Export last 2 hours
DB_PATH = '/home/jack/pizero_bikecomputer/log/log.db'

# Calculate cutoff time
cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_AGO)
cutoff_str = cutoff.strftime('%Y-%m-%d %H:%M:%S')

print(f"Exporting rides since: {cutoff_str}")

# Query to check what we'll export
con = sqlite3.connect(DB_PATH)
count = con.execute(
    "SELECT COUNT(*) FROM BIKECOMPUTER_LOG WHERE timestamp >= ?",
    (cutoff_str,)
).fetchone()[0]

print(f"Found {count} records")

if count == 0:
    print("No data to export!")
    sys.exit(1)

# Get actual timestamps
start_ts, end_ts = con.execute(
    "SELECT MIN(timestamp), MAX(timestamp) FROM BIKECOMPUTER_LOG WHERE timestamp >= ?",
    (cutoff_str,)
).fetchone()

print(f"Time range: {start_ts} to {end_ts}")
con.close()

# Generate output filename from start timestamp
start_dt = datetime.fromisoformat(start_ts.replace('+00:00', ''))
local_start = start_dt.replace(tzinfo=timezone.utc).astimezone()
filename_base = local_start.strftime('%Y-%m-%d_%H-%M-%S')
output_file = f'/home/jack/pizero_bikecomputer/log/{filename_base}.fit'

# Create filtered temp database and export
# ... (use the filtering code from section 3) ...

print(f"✓ Exported to: {output_file}")
```

---

### Use Case 2: Export Specific Lap

```python
#!/usr/bin/env python3
"""Export only a specific lap from a ride"""
import sys
import sqlite3
sys.path.insert(0, '/home/jack/pizero_bikecomputer')

from modules.logger.logger_fit import LoggerFit
from modules.logger.logger import Logger

LAP_NUMBER = 1
DB_PATH = '/home/jack/pizero_bikecomputer/log/log.db'

con = sqlite3.connect(DB_PATH)

# Check how many laps exist
max_lap = con.execute("SELECT MAX(lap) FROM BIKECOMPUTER_LOG").fetchone()[0]
print(f"Database has {max_lap + 1} laps (0-{max_lap})")

if LAP_NUMBER > max_lap:
    print(f"Lap {LAP_NUMBER} doesn't exist!")
    sys.exit(1)

# Get lap info
count, start_ts, end_ts = con.execute(
    "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM BIKECOMPUTER_LOG WHERE lap = ?",
    (LAP_NUMBER,)
).fetchone()

print(f"Lap {LAP_NUMBER}: {count} records from {start_ts} to {end_ts}")

# Create filtered temp database with only this lap
# ... (modify filtering code to filter by lap instead of timestamp) ...
```

---

### Use Case 3: Merge Multiple Databases

```python
#!/usr/bin/env python3
"""Merge data from multiple database backups into one export"""
import sys
import sqlite3
import glob

sys.path.insert(0, '/home/jack/pizero_bikecomputer')

# Find all database backups
db_backups = sorted(glob.glob('/home/jack/pizero_bikecomputer/log/log.db-*'))

print(f"Found {len(db_backups)} database backups")

# Create new temporary database
merged_db = '/tmp/merged_ride.db'

# Copy schema from first database
con_first = sqlite3.connect(db_backups[0])
schema = con_first.execute(
    "SELECT sql FROM sqlite_master WHERE type='table' AND name='BIKECOMPUTER_LOG'"
).fetchone()[0]
con_first.close()

con_merged = sqlite3.connect(merged_db)
con_merged.execute(schema)

# Merge all databases
total_records = 0
for db_path in db_backups:
    con = sqlite3.connect(db_path)
    records = con.execute("SELECT * FROM BIKECOMPUTER_LOG").fetchall()
    
    placeholders = ','.join(['?' for _ in range(len(records[0]))])
    con_merged.executemany(
        f"INSERT INTO BIKECOMPUTER_LOG VALUES ({placeholders})",
        records
    )
    total_records += len(records)
    print(f"  + {len(records)} records from {db_path}")
    con.close()

con_merged.commit()
con_merged.close()

print(f"\nTotal: {total_records} records merged")

# Now export the merged database
# ... (use normal export code) ...
```

---

## Testing Your Scripts

Before using custom scripts on real ride data:

1. **Test on a copy of the database**:
   ```bash
   cp log/log.db log/log.db.test
   # Run your script on log.db.test
   ```

2. **Verify the output**:
   ```bash
   file output.fit  # Should say "FIT Map data"
   ls -lh output.fit  # Check file size is reasonable
   ```

3. **Test upload** to one service first (not both):
   - Upload to RWGPS first (easier to delete activities)
   - Verify data looks correct
   - Then upload to Strava if all looks good

4. **Keep backups**:
   ```bash
   cp log/log.db log/log.db.backup-$(date +%Y%m%d)
   ```

---

## Archived Scripts

On the Pi, old custom scripts have been moved to `~/pizero_bikecomputer/custom_scripts_backup/`:
- `export_fit.py` - Simple export script
- `export_garmin.py` - Garmin-specific export
- `export_ride.py` - **The one that caused upload issues (missing .fit extension)**
- `test_export.py` - Export testing script
- `write_fit.py` - Low-level FIT writing

These are kept for reference but should NOT be used directly. They may contain bugs or use deprecated patterns.

---

## Need Help?

If you encounter issues with custom scripts:

1. Check the logs for warnings about filenames
2. Verify your database has the data you expect
3. Test with a small filtered dataset first
4. Refer to the official export script examples in `modules/logger/logger_fit.py`

---

**Last updated**: April 14, 2026  
**Status**: Active guidelines
