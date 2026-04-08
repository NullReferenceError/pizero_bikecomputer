# Display HAT Mini Setup Guide

This guide covers setting up the Pimoroni Display HAT Mini (v1 and 2.0) with pizero_bikecomputer on Raspberry Pi.

## Hardware Overview

- **Display**: Pimoroni Display HAT Mini (PIM589)
- **Resolution**: 320x240 pixels
- **Interface**: SPI (Serial Peripheral Interface)
- **Driver**: ST7789V2-based LCD
- **Colors**: 65K colors
- **Size**: 2.0" diagonal

## Button Layout

The Display HAT Mini has 4 tactile buttons:

| Button | GPIO | Physical Pin | Default Action (MAIN) | Long Press |
|--------|------|--------------|----------------------|-----------|
| A | GPIO 5 | 29 | scroll_prev | change_mode |
| B | GPIO 6 | 31 | count_laps | reset_count |
| X | GPIO 16 | 36 | scroll_next | enter_menu |
| Y | GPIO 24 | 18 | start_and_stop | - |

Note: Both v1 and v2.0 use identical GPIO button pins.

## Connection

The Display HAT Mini connects directly to the Raspberry Pi's SPI interface and GPIO header. No additional wiring required.

### GPIO Pin Usage

| Function | GPIO | Pin |
|----------|------|-----|
| Button A | GPIO 5 | 29 |
| Button B | GPIO 6 | 31 |
| Button X | GPIO 16 | 36 |
| Button Y | GPIO 24 | 18 |
| SPI MOSI | GPIO 10 | 19 |
| SPI SCLK | GPIO 11 | 23 |
| SPI CS | GPIO 8 | 24 |
| LCD DC | GPIO 9 | 21 |
| LCD TE | GPIO 25 | 22 |
| Backlight | GPIO 13 | 33 |

## Configuration

### Step 1: Enable SPI Interface

The Display HAT Mini requires SPI to be enabled:

```bash
sudo raspi-config
```

Navigate to:
- **Interface Options > SPI** > Select **Yes** to enable SPI

### Step 2: Add SPI dtoverlay (Optional)

The ST7789 driver typically loads automatically via the Display HAT Mini's EEPROM. However, if needed, you can add an explicit overlay:

Edit `/boot/firmware/config.txt` and add:

```bash
dtoverlay=spi0-1fps,pin_32=9,pin_33=10
```

### Step 3: Reboot

After enabling SPI, reboot:

```bash
sudo reboot
```

### Step 4: Verify Display

Check for framebuffer:

```bash
ls -la /dev/fb*
# Expected: /dev/fb0 (HDMI) and possibly /dev/fb1 if using fbcp
```

Check SPI device:

```bash
ls -la /dev/spi*
# Expected: /dev/spidev0.0 and /dev/spidev0.1
```

### Step 5: Configure pizero_bikecomputer

Edit your `setting.conf`:

```ini
[DISPLAY]
display = Display_HAT_Mini
```

Or use the install script:

```bash
./install.sh --display display-hat-mini --pyqt6 --services
```

## Optional: Rotation

To rotate the display 180 degrees, add to config.txt:

```bash
dtoverlay=spi0-1fps,pin_32=9,pin_33=10,rotate=180
```

## Troubleshooting

### Display not showing

1. Check SPI is enabled:
   ```bash
   raspi-config nonint do_spi 0
   lsmod | grep spi
   ```

2. Check dmesg for ST7789:
   ```bash
   dmesg | grep -i st7789
   ```

3. Try forcing framebuffer:
   ```bash
   sudo modprobe fbtft_device name=adafruit22a speed=16000000 gpios=dc:25,reset:24
   ```

### Buttons not responding

1. Check GPIO buttons are detected:
   ```bash
   gpio readall
   ```

2. Verify buttons are connected to correct GPIO pins (5, 6, 16, 24)

### Using fbcp for Mirroring

To mirror the desktop to the Display HAT Mini:

```bash
sudo apt install fbcp
```

Add to /etc/rc.local before exit 0:

```bash
fbcp &
```

## Quick Install Commands

The easiest way to set up:

```bash
# Full installation with Display HAT Mini
./install.sh --display display-hat-mini --pyqt6 --services -y

# Or manually enable SPI first, then run install
sudo raspi-config nonint do_spi 0
./install.sh --pyqt6 --services
# Then set display = Display_HAT_Mini in setting.conf
```