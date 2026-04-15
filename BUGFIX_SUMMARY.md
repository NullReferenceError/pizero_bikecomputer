# Bug Fix Summary - April 14, 2026

## Overview

This document summarizes the bugs discovered and fixed in the pizero_bikecomputer codebase during investigation of an upload failure on April 14, 2026.

## Root Cause Analysis

### The Issue
After completing a ride on April 14, 2026 (4:38pm-5:34pm MT), the upload to Strava/RWGPS failed. Investigation revealed:

1. **The ride was never properly reset** through the normal UI workflow
2. **A custom script** (`export_ride.py`) was used that:
   - Created a FIT file without `.fit` extension (`log/ride_april14`)
   - Exported wrong data (all of April 14, not just the evening ride)
   - Corrupted `setting.conf` by updating `upload_file` path incorrectly

3. **Multiple code bugs** were discovered that contributed to the issue

---

## Bugs Fixed

### Bug #1: Python Fallback Missing setting.conf Update ⚠️ MEDIUM SEVERITY

**File**: `modules/logger/logger_fit.py`  
**Lines**: 499-530 (after fix)

**Problem**:
The `write_log_python()` method (Python fallback when Cython is unavailable) only set the in-memory `G_UPLOAD_FILE` variable but did not persist it to `setting.conf`. This meant that if the system fell back to Python mode, the upload file path would be lost after restart.

**Fix Applied**:
Added the same setting.conf update logic from `write_log_cython()` to `write_log_python()`:
```python
# Bug Fix #1: Save to setting.conf to persist (same as Cython version)
try:
    setting_file = Setting.config_file
    with open(setting_file, "r") as f:
        lines = f.readlines()
    # ... update logic ...
    with open(setting_file, "w") as f:
        f.writelines(new_lines)
except Exception as e:
    app_logger.warning(f"Could not save upload_file to setting.conf: {e}")
```

**Testing**: Verified code structure matches Cython version

---

### Bug #2: Hardcoded Relative Path for setting.conf ⚠️ LOW SEVERITY

**File**: `modules/logger/logger_fit.py`  
**Lines**: 275, 506

**Problem**:
Both `write_log_cython()` and `write_log_python()` used a hardcoded relative path:
```python
setting_file = "setting.conf"  # Assumes current directory
```

This would fail if the bike computer was started from a different directory.

**Fix Applied**:
Changed to use the `Setting` class constant which is already defined in the codebase:
```python
# Bug Fix #2: Use Setting.config_file instead of hardcoded path
setting_file = Setting.config_file
```

**Testing**: Code compiles and runs successfully with new path resolution

---

### Bug #3: No Validation for Missing .fit Extension ⚠️ LOW SEVERITY

**File**: `modules/logger/logger_fit.py`  
**Lines**: 254-258, 303-307

**Problem**:
The FIT export functions accepted any filename without validating that it ended with `.fit`. This allowed custom scripts to create improperly named files.

**Fix Applied**:
Added validation warnings in both `write_log_cython()` and `write_log_python()`:
```python
# Bug Fix #3: Validate filename has .fit extension
if not filename.endswith('.fit'):
    app_logger.warning(
        f"FIT filename should end with .fit extension: {filename}"
    )
```

**Testing**: ✅ CONFIRMED - Warning appears when exporting with bad filename:
```
WARNING: FIT filename should end with .fit extension: /tmp/tmpxyz_no_extension
```

---

### Bug #4: Shadowed Module-Level Import (discovered during testing)

**File**: `modules/logger/logger_fit.py`  
**Line**: 298 (removed)

**Problem**:
The exception handler in `write_log_cython()` re-imported `app_logger`:
```python
except Exception as e:
    import app_logger  # ← This shadows the module-level import!
    app_logger.warning(...)
```

This caused `app_logger` to become a local variable in the function, making it unavailable in the earlier validation code (Bug Fix #3).

**Fix Applied**:
Removed the redundant import since `app_logger` is already imported at module level (line 20).

**Testing**: ✅ CONFIRMED - Validation warnings now work correctly

---

## Configuration Issues Fixed

### Issue #1: Corrupted setting.conf Structure

**Problem**:
The `upload_file` setting was placed after `[GARMINCONNECT_API]` section instead of in `[GENERAL]`:
```ini
[GARMINCONNECT_API]
email = 
password = 

upload_file = /home/jack/pizero_bikecomputer/log/ride_april14  # WRONG!
```

**Fix Applied**:
- Created export script that properly places `upload_file` in `[GENERAL]` section
- Script removes misplaced entries from other sections

**Result**:
```ini
[GENERAL]
display = Display_HAT_Mini
...
upload_file = /home/jack/pizero_bikecomputer/log/2026-04-14_16-38-37.fit  # ✓ CORRECT!

[BT]
...
```

---

### Issue #2: Wrong FIT File Content

**Problem**:
- File `log/ride_april14` contained data from entire April 14 (3,379 records)
- Included 488 records before the actual ride + 2,891 from the evening ride
- Missing `.fit` extension

**Fix Applied**:
- Created `export_april14_ride.py` script that:
  - Filters database to only records after 4pm MT (22:00 UTC)
  - Exports exactly 2,891 records from the target ride
  - Uses proper filename: `2026-04-14_16-38-37.fit`

**Result**:
✅ FIT file: 75,519 bytes containing only the evening ride data

---

## Testing Results

### Test 1: Export and Upload ✅ PASSED
- **Date**: April 14, 2026, 7:40pm MT
- **Export**: Successfully created `2026-04-14_16-38-37.fit` (75,519 bytes)
- **Upload to Strava**: ✅ SUCCESS
- **Upload to RWGPS**: ✅ SUCCESS
- **Local backup**: ✅ Downloaded to `downloaded_rides/`

### Test 2: Filename Validation Warning ✅ PASSED
- **Test**: Export with filename missing `.fit` extension
- **Result**: Warning logged: `WARNING: FIT filename should end with .fit extension`
- **Code**: Bug Fix #3 working correctly

### Test 3: setting.conf Update ✅ PASSED
- **Test**: Export creates proper `upload_file` entry in `[GENERAL]` section
- **Result**: `upload_file = /home/jack/pizero_bikecomputer/log/2026-04-14_16-38-37.fit`
- **Location**: Correctly placed after other `[GENERAL]` settings

---

## Files Modified

### Production Code
- `modules/logger/logger_fit.py` - Applied 4 bug fixes

### Temporary Scripts (created and deleted)
- `export_april14_ride.py` - Export filtered ride data
- `upload_ride_simple.py` - Upload to Strava/RWGPS
- `test_bugfixes.py` - Validate bug fixes

### Archived Scripts
- Moved 5 old custom scripts to `custom_scripts_backup/` on Pi:
  - `export_fit.py`
  - `export_garmin.py`
  - `export_ride.py` (the one that caused the issue)
  - `test_export.py`
  - `write_fit.py`

### Configuration
- `setting.conf` - Fixed structure, correct `upload_file` path
- `setting.conf.backup` - Backup of original corrupted version

---

## Recommendations

### For Users

1. **Always use the normal reset button** after completing a ride
   - This ensures proper FIT export
   - Database gets backed up correctly
   - Auto-upload triggers if enabled

2. **Avoid custom export scripts** unless necessary
   - If needed, follow the guidelines in `CUSTOM_SCRIPTS.md`
   - Always use `.fit` extension
   - Test thoroughly before relying on them

3. **Verify uploads succeeded**
   - Check Strava/RWGPS for the activity
   - Verify data looks correct (time, distance, power, HR)

### For Developers

1. **Consider making filename validation stricter**
   - Current fix: Warning only
   - Option: Auto-append `.fit` if missing
   - Option: Raise error and refuse export

2. **Add integration tests** for:
   - Python fallback path (when Cython unavailable)
   - setting.conf update mechanism
   - Filename validation

3. **Document the export API** properly
   - Expected filename format
   - When setting.conf gets updated
   - How to safely call export from custom scripts

4. **Add database state checks** before export
   - Warn if database contains multi-day data
   - Suggest using date filtering for partial exports

---

## Backward Compatibility

All fixes are **100% backward compatible**:
- ✅ No API changes
- ✅ No breaking changes to existing workflows
- ✅ Only adds validation warnings (non-blocking)
- ✅ Improves robustness of Python fallback path

---

## Summary

**Total bugs fixed**: 4  
**Lines changed**: ~50  
**Files modified**: 1 production file  
**Testing**: Validated with real ride data upload  
**Impact**: Prevents future upload failures, improves code robustness

The fixes ensure that both the Cython and Python code paths properly persist the upload file path to `setting.conf`, validate filenames, and use proper path resolution. Users will now see warnings if they use incorrect filenames, preventing silent failures.

---

**Document created**: April 14, 2026  
**Author**: OpenCode AI Assistant  
**Status**: Complete
