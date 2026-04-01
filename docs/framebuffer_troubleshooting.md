# Sharp Display Framebuffer Troubleshooting

## Problem

The Sharp Memory Display (Adafruit 2.7" 400x240) was not displaying anything when running `pizero_bikecomputer.py`.

## Root Cause Analysis

1. **Missing `sharp_drm` kernel module** - The Sharp display requires a DRM kernel driver to create `/dev/fb1`

2. **Only `/dev/fb0` existed** - HDMI framebuffer at fb0, no fb1 for Sharp display

3. **Bug in `install.sh`** - Lines 358-360 had redundant `envs` assignment:
   ```bash
   envs="Environment=\"QT_QPA_PLATFORM=offscreen\"\n"
   envs="Environment=\"QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0\"\n"  # Overwrites previous!
   ```

4. **Kernel module compilation failure** - The `sharp-drm` driver from ardangelo/sharp-drm-driver failed to compile:
   ```
   fatal error: drm/drm_fbdev_generic.h: No such file or directory
   ```
   This is due to kernel API changes in newer kernels (6.12+).

## Available Backends for Sharp MIP Displays

The codebase supports three backends for MIP displays:

1. **sharp-drm** (kernel module) - Uses DRM driver, requires `/dev/fb1`
2. **pigpio** (recommended for kernel 6.12+) - Uses userspace SPI, requires pigpiod daemon
3. **spidev + libgpiod** (fallback) - Uses SPI without pigpio

### Recommendation for Kernel 6.12+

Use **pigpio backend** - see "Solution: Use pigpio Backend Instead of DRM" above.

## Changes Made to `install.sh`

### 1. Fixed `envs` Overwrite Bug

Changed from:
```bash
else
    envs="Environment=\"QT_QPA_PLATFORM=offscreen\"\n"
    envs="Environment=\"QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0\"\n"
```

To:
```bash
else
    if [[ "$sharp_drm_loaded" == "true" ]]; then
        envs="Environment=\"QT_QPA_PLATFORM=linuxfb:fb=/dev/fb1\"\n"
    else
        envs="Environment=\"QT_QPA_PLATFORM=offscreen\"\n"
    fi
```

### 2. Added `check_sharp_drm()` Function

Detects:
- Module loaded with `/dev/fb1` available → return 0
- Module loaded but no `/dev/fb1` → return 1
- Module available but not loaded → return 2
- Module not available → return 3

### 3. Added `install_sharp_drm()` Function

Attempts to:
- Install kernel headers (handles missing `raspberrypi-kernel-headers` package)
- Clone `ardangelo/sharp-drm-driver`
- Build and install module
- Load with `modprobe`

### 4. Added `--sharp-drm` CLI Flag

```bash
./install.sh --no-venv --no-pyqt6 --services --sharp-drm -y
```

### 5. Added Full CLI Argument Parsing

```bash
./install.sh --help

Options:
    --venv              Setup Python virtual environment
    --venv-name NAME    Virtual environment name
    --pyqt6             Install PyQt6 packages
    --ant               Install ANT+ packages
    --gps               Install GPS packages
    --bluetooth         Install Bluetooth packages
    --i2c               Enable I2C
    --spi               Enable SPI
    --services          Install systemd services
    --xwindow           Use X11 instead of framebuffer
    --sharp-drm         Auto-install sharp_drm kernel module
    -y, --yes           Answer yes to all prompts
```

### 6. Fixed `pip install` Commands

Added `--break-system-packages` flag for Python 3.11+ externally-managed environments:
- `pip install --break-system-packages oyaml polyline`
- `pip install --break-system-packages qasync pyqtgraph`
- etc.

## Current Status

- **Working solution**: Use pigpio backend (not sharp-drm DRM driver)
- Set `display = MIP_Sharp_mono_400x240` and `USE_DRM = False` in setting.conf
- pigpio daemon must be running: `sudo systemctl enable pigpiod`

## Kernel 6.12+ DRM API Changes

Starting with kernel 6.12:
- `drm_fbdev_generic.h` removed → replaced with `drm_client.h` and `drm_client_setup.h`
- `drm_fbdev_generic_setup()` deprecated → use `drm_client_setup()`
- No `/dev/fb1` created → only `/dev/dri/card*`
- Qt linuxfb plugin fails because it expects fbdev devices (`/dev/fb*`)

### Problem Summary

1. sharp-drm kernel module loads but creates `/dev/dri/card0` (or card1), not `/dev/fb1`
2. Qt's linuxfb platform expects traditional framebuffer devices (`/dev/fb*`)
3. Even with DRM device available, Qt cannot render to it without proper DRM platform support
4. The sharp-drm driver causes dtoverlay segfaults on kernel 6.12+ when loaded

### Solution: Use pigpio Backend Instead of DRM

The pigpio backend communicates directly with the Sharp display via SPI:

1. **Disable sharp-drm**:
   ```bash
   # Comment out sharp-drm in /boot/firmware/config.txt
   #dtoverlay=sharp-drm
   ```

2. **Configure setting.conf**:
   ```ini
   [GENERAL]
   display = MIP_Sharp_mono_400x240
   
   [DISPLAY]
   USE_DRM = False
   ```

3. **Ensure pigpiod is running**:
   ```bash
   sudo systemctl enable pigpiod
   sudo systemctl start pigpiod
   ```

4. **Use offscreen Qt platform** (required for both backends):
   ```bash
   Environment="QT_QPA_PLATFORM=offscreen"
   ```

### Why This Works

- pigpio bypasses the kernel DRM entirely
- Communicates directly with display via userspace SPI
- Cython implementation (`mip_helper_pigpio`) compiles for optimal performance
- Works on all kernel versions

### What Doesn't Work on Kernel 6.12+

- sharp-drm kernel module (creates DRM device, not fbdev)
- `QT_QPA_PLATFORM=linuxfb:fb=/dev/dri/card*` (Qt doesn't support DRM devices)
- Any solution relying on `/dev/fb1` framebuffer device

## Future Work

1. Wait for Qt to add proper DRM/KMS platform support
2. Build custom Qt with DRM platform
3. Use older Raspberry Pi OS (Legacy) with kernel 6.1.x (has working fbdev)
