# GPIO Button Configuration

This document describes the physical button GPIO pin assignments for pizero_bikecomputer.

## Overview

The pizero_bikecomputer supports physical buttons through three methods:
1. **Direct GPIO pins** - Buttons connected directly to Raspberry Pi GPIO pins
2. **I2C Button Expanders** - MCP23008/MCP23009 or Button SHIM
3. **BLE/ANT+ Remote Controls** - Zwift Click V2, ANT+ remote controls

All GPIO pin numbers use **BCM mode** (Broadcom chip-specific numbering).

## Button Functions

| Function | Short Press | Long Press |
|----------|-------------|------------|
| **scroll_prev** | Navigate to previous page/screen | change_mode (some displays) |
| **scroll_next** | Navigate to next page/screen | enter_menu (some displays) |
| **count_laps** | Record a lap | reset_count (reset lap counter) |
| **start_and_stop_manual** | Start/stop activity recording | Quit application (some displays) |
| **brightness_control** | Adjust screen brightness | - |
| **enter_menu** | Open menu system | - |
| **back_menu** | Go back in menu | - |
| **get_screenshot** | Capture screenshot | - |
| **multiscan** | ANT+ multiscan mode | - |

## Direct GPIO Pin Assignments

### PiTFT Display

| BCM GPIO | Button | Short Press | Long Press |
|----------|--------|-------------|------------|
| **GPIO 5** | Left | scroll_prev | - |
| **GPIO 6** | Lap | count_laps | reset_count |
| **GPIO 12** | Brightness | brightness_control | - |
| **GPIO 13** | Start/Stop | start_and_stop_manual | - |
| **GPIO 16** | Right | scroll_next | enter_menu |

**Reference:** `modules/button_config.py` lines 225-239

---

### Papirus E-ink Display

| BCM GPIO | Button | Short Press | Long Press |
|----------|--------|-------------|------------|
| **GPIO 16** | SW1 (Left) | scroll_prev | - |
| **GPIO 26** | SW2 (Lap) | count_laps | reset_count |
| **GPIO 20** | SW3 (Start/Stop) | start_and_stop_manual | - |
| **GPIO 21** | SW4 (Right) | scroll_next | enter_menu |

**Note:** Papirus has external pull-up resistors, so internal pull-ups are NOT enabled.

**Reference:** `modules/button_config.py` lines 241-253

---

### DFRobot RPi Display

| BCM GPIO | Button | Short Press | Long Press |
|----------|--------|-------------|------------|
| **GPIO 21** | Button 1 | start_and_stop_manual | reset_count |
| **GPIO 20** | Button 2 | scroll_next | enter_menu |

**Reference:** `modules/button_config.py` lines 255-263

---

### Pirate Audio / Display HAT Mini

| BCM GPIO | Button | Short Press | Long Press |
|----------|--------|-------------|------------|
| **GPIO 5** | Button A | scroll_prev | change_mode |
| **GPIO 6** | Button B | count_laps | reset_count |
| **GPIO 16** | Button X | scroll_next | enter_menu |
| **GPIO 24** | Button Y | start_and_stop_manual | - |

**Reference:** `modules/button_config.py` lines 265-295

---

### Pirate Audio (Old Revision)

Same as Pirate Audio above, except:

| BCM GPIO | Button | Short Press | Long Press |
|----------|--------|-------------|------------|
| **GPIO 20** | Button Y | start_and_stop_manual | - |

**Note:** Older Pirate Audio boards use GPIO 20 instead of GPIO 24 for Button Y.

**Reference:** `modules/button_config.py` lines 297, 324-328

---

## I2C Button Expanders

### MCP23008 / MCP23009

The MCP23008 is an 8-port GPIO expander connected via I2C.

**I2C Addresses:**
- MCP23008: `0x20`
- MCP23009: `0x27`

**Pin Mapping:**

| MCP Pin | Button Label | Short Press | Long Press |
|---------|--------------|-------------|------------|
| **GP0** | A | scroll_prev | get_screenshot |
| **GP1** | B | count_laps | reset_count |
| **GP2** | C | multiscan | toggle_fake_trainer |
| **GP3** | D | start_and_stop_manual | - |
| **GP4** | E | scroll_next | enter_menu |

**Optional Interrupt Pin:**
- BCM GPIO 23 can be used as interrupt pin for faster button response
- Currently commented out in code - requires uncommenting in `modules/sensor/sensor_i2c.py` line 1913

**Reference:** 
- `modules/sensor/i2c/MCP230XX.py` lines 315-322
- `modules/sensor/sensor_i2c.py` line 1913

---

### Pimoroni Button SHIM

The Button SHIM is an I2C button board with 5 buttons (A-E) and an RGB LED.

**Button Mapping:**

| Button | Short Press | Long Press |
|--------|-------------|------------|
| **A** | scroll_prev | get_screenshot |
| **B** | count_laps | reset_count |
| **C** | multiscan | toggle_fake_trainer |
| **D** | start_and_stop_manual | - |
| **E** | scroll_next | enter_menu |

**LED Control:** RGB LED can be controlled programmatically

**Installation:**
```bash
sudo apt install python3-buttonshim
```

**Reference:** `modules/sensor/i2c/button_shim.py`

---

## BLE/ANT+ Remote Controls

### Zwift Click V2 (BLE)

The Zwift Click V2 is a Bluetooth LE remote control with left/right buttons.

**Button Mapping:**
- Left button: Maps to button functions via `button_config.py`
- Right button: Maps to button functions via `button_config.py`

**Reference:** `modules/sensor/sensor_ble.py` lines 86-119

---

### ANT+ Remote Controls

ANT+ remote controls (like bike computer remotes) can send button press events.

**Supported Events:**
- LAP button (0x0024)
- PAGE button (0x0001)
- PAGE button long press (0x0000)
- CUSTOM button (0x8000)
- CUSTOM button long press (0x8001)

**Reference:** `modules/sensor/ant/ant_device_ctrl.py` lines 22-50

---

## GPIO Hardware Configuration

### GPIO Chip Path
- **Raspberry Pi 5 / gpiod v2:** `/dev/gpiochip4`
- **Older Raspberry Pi:** `/dev/gpiochip0`

**Reference:** `modules/sensor/sensor_gpio.py` line 23

### Debounce Time
- **Default:** 250ms software debounce
- Prevents accidental double-presses

**Reference:** `modules/sensor/sensor_gpio.py` line 27

### Pull-up Resistors

**Displays requiring internal pull-up resistors:**
- PiTFT
- DFRobot_RPi_Display
- Pirate_Audio_old
- Pirate_Audio
- Display_HAT_Mini

**Displays with external pull-up (no internal pull-up):**
- Papirus

**Reference:** `modules/sensor/sensor_gpio.py` lines 38-48

---

## Long Press Threshold

**Default:** 1.0 seconds

To change, edit `modules/button_config.py` line 10:
```python
_G_LONG_PRESS_THRESHOLD_SEC = 1.0
```

---

## Button Mode System

The button system supports different modes for different contexts:

### Main Modes:
- **MAIN** - Normal cycling mode (navigate pages, record laps, start/stop)
- **MAP** - Map interaction mode (zoom, pan)
- **MENU** - Menu navigation mode (tab, space, back)
- **COURSE_PROFILE** - Course profile view mode
- **ANT+_SEARCH** - ANT+ sensor search mode

Button functions automatically change based on the current mode.

**Reference:** `modules/button_config.py` lines 13-18

---

## Making GPIO Pins Configurable

### Current Status: HARDCODED ⚠️

All GPIO pin assignments are currently hardcoded in `modules/button_config.py` and cannot be changed without editing source code.

### Future Enhancement

To make GPIO pins user-configurable, add a `[GPIO_BUTTONS]` section to `setting.conf`:

```ini
[GPIO_BUTTONS]
scroll_prev = 5
count_laps = 6
brightness_control = 12
start_and_stop_manual = 13
scroll_next = 16
```

**Implementation needed:**
1. Add GPIO configuration loading in `modules/helper/setting.py`
2. Update `modules/button_config.py` to read from config instead of hardcoded values
3. Add validation to prevent GPIO conflicts
4. Document safe GPIO pins to use (avoid I2C, SPI, UART pins)

---

## Troubleshooting

### Enable GPIO Debug Logging

To see detailed GPIO button debug messages, edit `modules/app_logger.py`:

```python
# Change this line:
app_logger.setLevel(level=logging.INFO)

# To this:
app_logger.setLevel(level=logging.DEBUG)
```

Then restart the service. You'll see messages like:
- `[GPIO] Button pins to monitor: [5, 6, 13, 19]`
- `[GPIO] Edge event detected on GPIO 5`
- `[GPIO] GPIO 5 button pressed`

### Buttons Not Working

1. **Check display type is set correctly in setting.conf:**
   ```ini
   [DISPLAY]
   display = PiTFT
   ```

2. **Verify GPIO permissions:**
   ```bash
   sudo usermod -a -G gpio $USER
   # Log out and log back in
   ```

3. **Check if gpiod is installed:**
   ```bash
   pip install gpiod
   ```

4. **Test GPIO manually:**
   ```bash
   gpioinfo | grep -E "gpiochip|line"
   ```

5. **Check for GPIO conflicts:**
   - I2C pins (GPIO 2, 3)
   - SPI pins (GPIO 7, 8, 9, 10, 11)
   - UART pins (GPIO 14, 15)

### I2C Button Expander Not Detected

1. **Enable I2C:**
   ```bash
   sudo raspi-config
   # Interface Options -> I2C -> Enable
   ```

2. **Check I2C devices:**
   ```bash
   i2cdetect -y 1
   # Should show device at 0x20 (MCP23008) or 0x27 (MCP23009)
   ```

3. **Install I2C tools:**
   ```bash
   sudo apt install i2c-tools python3-smbus
   ```

---

## Safe GPIO Pins for Custom Buttons

When adding custom button configurations, use these safe GPIO pins:

**Safe to use (no built-in functions):**
- GPIO 5, 6, 12, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27

**Avoid these pins:**
- GPIO 0, 1 (reserved for ID EEPROM)
- GPIO 2, 3 (I2C - SDA, SCL)
- GPIO 7, 8, 9, 10, 11 (SPI)
- GPIO 14, 15 (UART)
- GPIO 28-45 (internal use on Compute Module)

**Reference:** [Raspberry Pi GPIO Pinout](https://pinout.xyz/)

---

## Related Documentation

- [Framebuffer Troubleshooting](framebuffer_troubleshooting.md) - Display setup
- [Installation Guide](../install.sh) - Hardware setup
- [Button Config Source](../modules/button_config.py) - Button function definitions
- [GPIO Sensor Source](../modules/sensor/sensor_gpio.py) - GPIO hardware interface

---

## Hardware Wiring Diagrams

### Basic Button Connection

**With internal pull-up (recommended - simpler wiring):**
```
GPIO Pin ── Button ── GND
```

**With external pull-up resistor:**
```
3.3V ──[10kΩ]── GPIO Pin ── Button ── GND
```

**Notes:** 
- Most displays (PiTFT, Pirate Audio, MIP Sharp) use internal pull-ups, so external resistors are NOT needed
- Only Papirus requires external pull-up resistors
- Buttons are active-LOW: pressed = GPIO reads LOW (0V)

### Active Low vs Active High

All buttons in pizero_bikecomputer are **active LOW**:
- Button not pressed: GPIO reads HIGH (3.3V via pull-up)
- Button pressed: GPIO reads LOW (connected to ground)

---

## Version Information

- **Document Version:** 1.0
- **Last Updated:** 2026-04-02
- **Compatible with:** pizero_bikecomputer v3.x

---

## Contributing

If you add support for new button hardware, please update this documentation with:
1. GPIO pin assignments
2. Hardware setup instructions
3. Any special configuration needed
4. Photos of hardware connection (if applicable)

Submit documentation updates via pull request to the main repository.
