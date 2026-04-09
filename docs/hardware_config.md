# Hardware Configuration - Pi Zero 2 W Bike Computer

**Date Configured**: 2026-04-08  
**Device**: Raspberry Pi Zero 2 W Rev 1.0  
**Serial**: 7012DBFF

## I2C Configuration

### Bus Configuration
- **I2C Bus**: Bus 1 (GPIO 2/3 - pins SDA/SCL)
- **Device Node**: `/dev/i2c-1`
- **Enabled via**: `dtparam=i2c_arm=on` in `/boot/firmware/config.txt`

### Important Note
Previously, `dtparam=i2c_arm=off` was set, which disabled the standard I2C1 bus on GPIO 2/3. This caused all Qwiic sensors to be undetectable because they were physically connected but the I2C bus was disabled. Setting `i2c_arm=on` resolved this issue.

---

## Working Sensors ✅

### ISM330DHCX - 6-Axis IMU (Address: 0x6B)
- **Type**: 3-axis accelerometer + 3-axis gyroscope
- **Board**: SparkFun 9DoF IMU Breakout SEN-19895
- **Library**: adafruit-circuitpython-lsm6ds (v4.6.2)
- **Status**: ✅ Fully functional
- **Data Available**:
  - Acceleration (m/s²): X, Y, Z axes
  - Angular velocity (rad/s): X, Y, Z axes
- **Test Results**:
  - Acceleration: X=-0.50, Y=-7.03, Z=7.04 m/s² (realistic values)
  - Gyro: X=0.01, Y=-0.01, Z=-0.00 rad/s (near zero when stationary)

### VCNL4040 - Proximity/Light Sensor (Address: 0x60)
- **Type**: Ambient light + proximity sensor
- **Library**: adafruit-circuitpython-vcnl4040 (v1.2.23, pre-installed)
- **Status**: ✅ Fully functional
- **Data Available**:
  - Ambient light (lux)
  - Proximity (raw value)
- **Test Results**:
  - Successfully detected and reading values

### SAM-M8Q - GPS Module
- **Type**: u-blox GPS receiver
- **Interface**: UART (/dev/ttyAMA0 → /dev/serial0)
- **Driver**: GPSD (version 3.25)
- **Status**: ✅ Functional (requires outdoor test for satellite acquisition)
- **Config**: `/etc/default/gpsd` configured for /dev/serial0
- **Note**: GPS communication working, but satellite fix requires clear sky view

---

## Known Issues ⚠️

### PiSugar3 - Battery Monitor (Address: 0x57)
- **Expected**: PiSugar3 battery/UPS board
- **Status**: ⚠️ Installed but not detected on I2C bus
- **Issue**: Communication problem - cause unknown
- **Impact**: Battery monitoring unavailable
- **Priority**: Low (investigate later)
- **Possible Causes**:
  - Different I2C address than expected
  - Power/connection issue
  - Wrong PiSugar model (2 vs 3)

### MMC5983MA - Magnetometer (Address: 0x30)
- **Expected**: 3-axis magnetometer (part of SEN-19895 board with ISM330DHCX)
- **Status**: ⚠️ Not detected on I2C bus
- **Possible Causes**:
  1. Requires separate initialization sequence
  2. Different I2C address than expected
  3. Board variant without magnetometer
  4. Hardware issue
- **Impact**: No compass/heading functionality
- **Priority**: Nice to have (investigate later if compass needed)

### Device at 0x42
- **Status**: ❓ Responds to I2C but returns 0xFF for all registers
- **Action**: Ignored (likely unused address or improperly initialized device)

---

## Python Dependencies

### Installed Libraries
```
# Core CircuitPython support
adafruit-blinka==9.0.4
Adafruit-PlatformDetect==3.88.0
Adafruit-PureIO==1.1.11

# Sensor libraries
adafruit-circuitpython-lsm6ds==4.6.2        # ISM330DHCX
adafruit-circuitpython-vcnl4040==1.2.23     # VCNL4040

# Supporting libraries
adafruit-circuitpython-busdevice==5.2.16
adafruit-circuitpython-register==1.11.2
adafruit-circuitpython-typing==1.12.3
```

### Installation Commands
```bash
source /home/jack/.venv/bin/activate
pip install adafruit-blinka
pip install adafruit-circuitpython-lsm6ds
# adafruit-circuitpython-vcnl4040 was already installed
```

---

## I2C Bus Scan Results

```
$ sudo i2cdetect -y 1
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:                         -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- 42 -- -- -- -- -- -- -- -- -- -- -- -- --
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: 60 -- -- -- -- -- -- -- -- -- -- 6b -- -- -- --
70: -- -- -- -- -- -- -- --
```

**Detected Devices**:
- `0x42`: Unknown (returns 0xFF, ignored)
- `0x60`: VCNL4040 (light/proximity sensor) ✅
- `0x6B`: ISM330DHCX (IMU) ✅

**Missing Devices**:
- `0x30`: MMC5983MA magnetometer ⚠️
- `0x57`: PiSugar3 battery monitor ⚠️

---

## Bikecomputer Detection Log

From `/home/jack/pizero_bikecomputer/log/debug.log`:
```
2026-04-08 22:40:42 INFO: detected sensor modules:
2026-04-08 22:40:42 INFO:   ANT
2026-04-08 22:40:42 INFO:   GPIO (gpiod)
2026-04-08 22:40:42 INFO:   I2C
2026-04-08 22:40:43 INFO: detected I2C sensors:
2026-04-08 22:40:43 INFO:   MOTION: ISM330DHCX
2026-04-08 22:40:43 INFO:   LIGHT: VCNL4040
```

✅ **Both sensors successfully detected by bikecomputer application!**

---

## Troubleshooting

### If sensors not detected:
1. **Verify I2C enabled**: `ls -la /dev/i2c-1` should exist
2. **Check config.txt**: Ensure `dtparam=i2c_arm=on` is set
3. **Reboot**: `sudo reboot` (I2C changes require reboot)
4. **Scan I2C bus**: `sudo i2cdetect -y 1`
5. **Check physical connections**: Verify Qwiic cables are seated properly on both ends
6. **Check service logs**: `tail -f /home/jack/pizero_bikecomputer/log/debug.log`

### If GPS has no fix:
1. **Test outdoors**: GPS requires clear sky view for satellite acquisition
2. **Cold start**: First fix can take 30-60 seconds
3. **Check GPSD status**: `systemctl status gpsd`
4. **Monitor GPS data**: Use test script from TODO.md
5. **Verify device**: `ls -la /dev/serial0` should point to `/dev/ttyAMA0`

### If IMU data seems incorrect:
1. **Check orientation**: Sensor orientation affects acceleration/gyro readings
2. **Calibration**: May need magnetometer calibration if added later
3. **Check logs**: Look for I2C errors in debug.log
4. **Restart service**: `sudo systemctl restart pizero_bikecomputer.service`

---

## Future Work

- [ ] Investigate PiSugar3 detection issue (check I2C address with oscilloscope/logic analyzer)
- [ ] Debug MMC5983MA magnetometer (try different initialization sequences)
- [ ] Identify device at 0x42 if it becomes relevant
- [ ] Outdoor GPS test for satellite acquisition verification
- [ ] Add magnetometer support if MMC5983MA becomes available
- [ ] Consider alternative magnetometer if MMC5983MA cannot be enabled

---

## System Information

**Hardware**:
- Raspberry Pi Zero 2 W Rev 1.0
- Serial: 7012DBFF
- Display: Display_HAT_Mini (ST7789)

**Software**:
- OS: Raspberry Pi OS
- Python: 3.13.5
- Qt version: 6.8.2 (PyQt6)
- GPSD: 3.25

**GPIO Usage**:
- GPIO 2/3: I2C1 (SDA/SCL) for Qwiic sensors
- GPIO 5, 6, 16, 24: Button inputs
- UART (GPIO 14/15): SAM-M8Q GPS via /dev/ttyAMA0

---

## Success Criteria ✅

All primary objectives achieved:
- [x] I2C bus 1 enabled and functional
- [x] adafruit-blinka installed and working
- [x] adafruit-circuitpython-lsm6ds installed
- [x] ISM330DHCX provides acceleration + gyroscope data
- [x] VCNL4040 provides light + proximity data
- [x] GPS communicates via GPSD (outdoor test pending)
- [x] Bikecomputer service detects both I2C sensors
- [x] No I2C errors in logs
- [x] Documentation created

**Result**: Bike computer is now fully operational with working IMU and light sensors! 🎉
