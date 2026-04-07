# HyperPixel 4.0 Display Setup Guide

This guide covers setting up the Pimoroni HyperPixel 4.0" touchscreen display with pizero_bikecomputer on Raspberry Pi.

## Hardware Overview

- **Display**: Pimoroni HyperPixel 4.0" Touchscreen
- **Resolution**: 800x480 pixels
- **Interface**: DPI (Display Pixel Interface) via built-in kernel driver
- **Touch**: Capacitive multi-touch (Touch version)
- **Frame rate**: 60 FPS
- **Colors**: 18-bit (262,144 colors)
- **Driver**: `vc4-kms-dpi-hyperpixel4` (built-in, no custom build needed)

## Connection

The HyperPixel 4.0 connects directly to the Raspberry Pi's DPI interface and GPIO pins. No additional wiring is required beyond mounting the display onto the Pi's header.

## Kernel Driver Configuration

### Step 1: Add dtoverlay to config.txt

Edit `/boot/firmware/config.txt` and add the following line at the end:

```bash
dtoverlay=vc4-kms-dpi-hyperpixel4:rotate=1
```

### Rotation Options

The display defaults to portrait mode. Use the rotate parameter to set your preferred orientation:

| Value | Orientation | USB ports location |
|-------|-------------|-------------------|
| 0 | Normal (portrait) | Top |
| 1 | 90° (landscape) | **Bottom (Recommended)** |
| 2 | 180° (inverted portrait) | Bottom |
| 3 | 270° (landscape) | Top |

**Recommended**: `rotate=1` for landscape with USB ports at the bottom.

### Step 2: Keep vc4-kms-v3d enabled for desktop

The HyperPixel requires the VC4 driver to be loaded. Keep both overlays in config.txt:

```bash
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dpi-hyperpixel4:rotate=1
```

### Step 3: Reboot

After saving config.txt, reboot the Raspberry Pi:

```bash
sudo reboot
```

### Step 3: Verify display

Check that the display is detected at the correct resolution:

```bash
cat /sys/class/graphics/fb0/mode
# Expected: U:800x480p-60 or U:480x800p-60
```

## Display Rotation (Important!)

The dtoverlay rotation parameter may not work correctly on all Raspberry Pi models (particularly Pi Zero 2 W). If the display appears in portrait mode instead of landscape:

### Method 1: Use Screen Configuration Utility (Recommended)

1. From the Raspberry Pi desktop, go to **Preferences > Control Centre > Screen Configuration**
2. In the Screen Configuration dialog, find **DPI-1** under Screens
3. Right-click and select **Orientation > Landscape**
4. Click **Apply** and then **OK**
5. Restart the system for changes to persist

### Method 2: Manual xorg Configuration

Create `/usr/share/X11/xorg.conf.d/99-hyperpixel-rotation.conf`:

```xorg
Section "Monitor"
    Identifier "DPI-1"
    Option "Rotate" "left"
EndSection
```

Note: The Screen Configuration utility method is more reliable and will persist after reboot.

## Touch Configuration

### Verify touch device

After boot, verify the touchscreen is detected:

```bash
xinput list
```

Expected output includes: `Goodix Capacitive TouchScreen`

### Touch rotation

If you rotated the display, you may need to rotate the touch input to match. For landscape mode (rotate=1), create `/usr/share/X11/xorg.conf.d/88-hyperpixel4.conf`:

```xorg
Section "InputClass"
    Identifier "libinput HyperPixel4 Touch"
    MatchProduct "Goodix Capacitive TouchScreen"
    Option "CalibrationMatrix" "0 -1 1 1 0 0 0 0 1"
EndSection

Section "Monitor"
    Identifier "DSI-1"
    Option "Rotate" "left"
EndSection
```

Alternatively, use the Pimoroni rotation command:

```bash
DISPLAY=:0.0 hyperpixel4-rotate left
```

## I2C Implications

### Standard I2C is Disabled

HyperPixel 4.0 uses all GPIO pins for the display interface. This means:

- **Standard I2C (GPIO 2/3) is disabled**
- I2C sensors connected to the standard header will not work

### Solutions for I2C Sensors

**Option 1: Use QWIIC Connector**

The HyperPixel board has a QWIIC (STEMMA QT) connector for I2C devices. Use this for sensors like:
- BME280/BME680 (temperature, humidity, pressure)
- TSL2591 (light sensor)
- GPS modules (with appropriate configuration)

**Option 2: Use Alternate I2C Header**

The HyperPixel board provides an alternate I2C header using GPIO 19 (SCL) and GPIO 26 (SDA). This appears as `i2c-3` on Raspberry Pi OS.

Enable in config.txt:
```bash
dtoverlay=i2c3
```

Then detect devices:
```bash
i2cdetect -y 3
```

## Auto-Detection

pizero_bikecomputer automatically detects the HyperPixel 4.0 display by checking the framebuffer resolution. When the display is connected and enabled, the application should automatically use it.

If auto-detection doesn't work, you can manually set the display type in `setting.conf`:

```ini
[DISPLAY]
display = HyperPixel_4
```

## Backlight Control

The HyperPixel 4.0 supports basic backlight control (on/off). The backlight can be controlled:

1. **Automatically** - via the auto-backlight feature based on ambient light sensor
2. **Manually** - using the brightness button mapped to a GPIO button

The backlight is controlled via `/sys/class/backlight/rpi_backlight/brightness`:
- `0` = off
- `1` = on

Note: The HyperPixel backlight is binary (on/off only), not variable brightness.

## Running with X11

For the best touch experience, run pizero_bikecomputer with X11:

```bash
QT_QPA_PLATFORM=xcb python pizero_bikecomputer.py
```

Or use the `--xwindow` flag when running install.sh:
```bash
./install.sh --xwindow --hyperpixel
```

## Troubleshooting

### Display shows nothing after boot

1. Verify the dtoverlay is added correctly:
   ```bash
   cat /boot/firmware/config.txt | grep hyperpixel
   ```

2. Check framebuffer resolution:
   ```bash
   cat /sys/class/graphics/fb0/mode
   ```
   Should show `U:800x480p-60`

3. Reboot after adding dtoverlay

### Touch not working

1. Verify touch device is detected:
   ```bash
   xinput list | grep -i touch
   ```

2. Check touch rotation settings (if display is rotated)

3. Try using X11 platform instead of framebuffer

### I2C sensors not detected

1. Verify standard I2C is disabled:
   ```bash
   i2cdetect -y 1
   # Should show: Error: Could not open file `/dev/i2c-1'
   ```

2. Check alternate I2C bus (if configured):
   ```bash
   i2cdetect -y 3
   ```

3. Use QWIIC connector for sensors instead of standard GPIO header

## Quick Reference

```bash
# Enable HyperPixel during installation
./install.sh --display hyperpixel --pyqt6 --services --xwindow

# Manual config.txt setup (both overlays required!)
sudo tee -a /boot/firmware/config.txt << 'EOF'
dtoverlay=vc4-kms-v3d
dtoverlay=vc4-kms-dpi-hyperpixel4:rotate=1
EOF

# Disable I2C (required by HyperPixel)
sudo raspi-config nonint do_i2c 1

# Reboot required
sudo reboot

# Verify display resolution
cat /sys/class/graphics/fb0/mode

# Check touch device
xinput list | grep -i touch
```
