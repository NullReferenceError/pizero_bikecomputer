# Sensor Integration Execution Plan

**Date**: 2026-04-08  
**Device**: Raspberry Pi Zero 2 W (Serial: 7012DBFF)  
**Status**: Ready to execute

## Current Status

### Detected on I2C Bus 1:
- ✅ ISM330DHCX at 0x6B (IMU - accelerometer + gyroscope)
- ✅ VCNL4040 at 0x60 (proximity + light sensor)
- ❓ Device at 0x42 (returns 0xFF - unknown/ignored)

### Missing Libraries:
- ❌ adafruit-blinka (CircuitPython compatibility)
- ❌ adafruit-circuitpython-lsm6ds (ISM330DHCX driver)

### Known Issues:
- ⚠️ PiSugar3 (0x57): Installed but not detected - communication issue
- ⚠️ MMC5983MA (0x30): Magnetometer not detected - nice-to-have
- ✅ SAM-M8Q GPS: On UART via GPSD (needs outdoor test for fix)

---

## PHASE 1: Install Python Libraries (5 min)

### Step 1.1: Install Adafruit Blinka
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && pip install adafruit-blinka"
```
**Expected**: "Successfully installed adafruit-blinka..."

### Step 1.2: Verify Blinka
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && python3 -c 'import board; import busio; print(\"✓ Blinka installed\")'"
```
**Expected**: "✓ Blinka installed"

### Step 1.3: Install ISM330DHCX Library
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && pip install adafruit-circuitpython-lsm6ds"
```
**Expected**: "Successfully installed adafruit-circuitpython-lsm6ds..."

### Step 1.4: Verify ISM330DHCX Library
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && python3 -c 'import adafruit_lsm6ds.ism330dhcx; print(\"✓ ISM330DHCX library installed\")'"
```
**Expected**: "✓ ISM330DHCX library installed"

---

## PHASE 2: Test Sensors Independently (5 min)

### Step 2.1: Stop Bikecomputer Service
```bash
ssh jack@10.11.12.113 "sudo systemctl stop pizero_bikecomputer.service"
```
**Why**: Prevent I2C bus conflicts during testing

### Step 2.2: Test ISM330DHCX
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && python3 << 'EOF'
import board
import busio
import adafruit_lsm6ds.ism330dhcx

print('=== Testing ISM330DHCX at 0x6B ===')
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_lsm6ds.ism330dhcx.ISM330DHCX(i2c, address=0x6B)

acc = sensor.acceleration
gyro = sensor.gyro

print(f'Acceleration X={acc[0]:.2f}, Y={acc[1]:.2f}, Z={acc[2]:.2f} m/s^2')
print(f'Gyro X={gyro[0]:.2f}, Y={gyro[1]:.2f}, Z={gyro[2]:.2f} rad/s')
print('✓ ISM330DHCX is working!')
EOF
"
```
**Expected**: Real acceleration values (Z ≈ 9.8 m/s² when stationary)

### Step 2.3: Test VCNL4040
```bash
ssh jack@10.11.12.113 "source /home/jack/.venv/bin/activate && python3 << 'EOF'
import board
import busio
import adafruit_vcnl4040

print('=== Testing VCNL4040 at 0x60 ===')
i2c = busio.I2C(board.SCL, board.SDA)
sensor = adafruit_vcnl4040.VCNL4040(i2c)

lux = sensor.lux
prox = sensor.proximity

print(f'Ambient light: {lux} lux')
print(f'Proximity: {prox}')
print('✓ VCNL4040 is working!')
EOF
"
```
**Expected**: Light level (varies by room) and proximity value

---

## PHASE 3: Bikecomputer Integration (3 min)

### Step 3.1: Restart Service
```bash
ssh jack@10.11.12.113 "sudo systemctl start pizero_bikecomputer.service"
```

### Step 3.2: Wait for Initialization
```bash
sleep 10
```

### Step 3.3: Check Detection Logs
```bash
ssh jack@10.11.12.113 "grep -A 5 'detected I2C sensors:' /home/jack/pizero_bikecomputer/log/debug.log | tail -20"
```
**Expected**:
```
detected I2C sensors:
  ISM330DHCX(Accel / Gyro)
  VCNL4040(Light)
```

### Step 3.4: Verify Continuous Operation
```bash
ssh jack@10.11.12.113 "tail -20 /home/jack/pizero_bikecomputer/log/debug.log"
```
**Look for**: No I2C errors, sensors updating

---

## PHASE 4: GPS Verification (2 min)

### Step 4.1: Test GPS Data
```bash
ssh jack@10.11.12.113 "python3 << 'EOF'
import gps
import time

print('=== Testing GPS via GPSD ===')
session = gps.gps(mode=gps.WATCH_ENABLE)

print('Checking for GPS data (15 second timeout)...')
found_tpv = False

for i in range(15):
    try:
        report = session.next()
        
        if report['class'] == 'TPV':
            found_tpv = True
            mode = report.get('mode', 0)
            if mode >= 2:
                lat = report.get('lat', 'N/A')
                lon = report.get('lon', 'N/A')
                sats = report.get('satellites_used', 0)
                print(f'✓ GPS FIX: Mode={mode}, Sats={sats}, Lat={lat}, Lon={lon}')
                break
            else:
                print(f'GPS data present but no fix yet (mode={mode})')
                
    except KeyError:
        pass
    time.sleep(1)

if found_tpv:
    print('✓ GPS communication working')
else:
    print('⚠ No GPS data - check connection')

session.close()
EOF
"
```
**Expected**: GPS communication working (fix requires outdoor test)

---

## PHASE 5: Documentation (3 min)

### Step 5.1: Create Hardware Config Doc
Create `docs/hardware_config.md` with:
- I2C configuration details
- Working sensor list (ISM330DHCX, VCNL4040, SAM-M8Q)
- Known issues (PiSugar3, MMC5983MA)
- Troubleshooting guide

### Step 5.2: Update TODO Status
Mark completed tasks in this file

---

## PHASE 6: Git Commit (2 min)

### Step 6.1: Stage Files
```bash
git add docs/hardware_config.md TODO.md
```

### Step 6.2: Create Commit
```bash
git commit -m "Enable I2C sensors: ISM330DHCX IMU and VCNL4040 light sensor

Hardware configuration:
- Enabled I2C1 bus via dtparam=i2c_arm=on in /boot/firmware/config.txt
- I2C1 (GPIO 2/3) now available as /dev/i2c-1 for Qwiic sensors

Software dependencies:
- Installed adafruit-blinka (CircuitPython compatibility layer)
- Installed adafruit-circuitpython-lsm6ds (ISM330DHCX support)
- adafruit-circuitpython-vcnl4040 was already installed

Working sensors:
✅ ISM330DHCX at 0x6B: 6-axis IMU (accelerometer + gyroscope)
✅ VCNL4040 at 0x60: Proximity and ambient light sensor
✅ SAM-M8Q GPS via GPSD on /dev/ttyAMA0 (UART)

Known issues documented:
⚠️ PiSugar3 battery monitor (0x57): Not detected - communication issue
⚠️ MMC5983MA magnetometer (0x30): Not detected - investigation needed
❓ Device 0x42: Unidentified (returns 0xFF) - ignored for now

Tested on: Raspberry Pi Zero 2 W Rev 1.0 (Serial: 7012DBFF)
Date: 2026-04-08"
```

---

## Success Criteria

- [x] I2C bus 1 enabled and functional
- [ ] adafruit-blinka installed
- [ ] adafruit-circuitpython-lsm6ds installed
- [ ] ISM330DHCX provides acceleration + gyroscope data
- [ ] VCNL4040 provides light + proximity data
- [ ] GPS communicates via GPSD
- [ ] Bikecomputer service detects both sensors
- [ ] No I2C errors in logs
- [ ] Documentation created
- [ ] Git commit created

---

## Rollback Plan

**If library installation fails**:
```bash
pip uninstall adafruit-blinka adafruit-circuitpython-lsm6ds
sudo systemctl restart pizero_bikecomputer.service
```

**If sensors don't work**:
```bash
sudo systemctl restart pizero_bikecomputer.service
tail -f /home/jack/pizero_bikecomputer/log/debug.log
```

**If git commit has issues**:
```bash
git reset --soft HEAD~1  # Undo commit, keep changes
# OR
git reset --hard HEAD~1  # Undo commit, lose changes
```

---

## Future Work

- [ ] Investigate PiSugar3 detection issue (0x57)
- [ ] Debug MMC5983MA magnetometer (0x30) if needed
- [ ] Identify device at 0x42 if it becomes relevant
- [ ] Outdoor GPS test for satellite acquisition
- [ ] Consider alternative magnetometer if MMC5983MA unavailable

---

## Notes

- **Estimated total time**: 15-20 minutes
- **Risk level**: Low (isolated venv, reversible changes)
- **Code changes**: None required (existing code already supports sensors)
- **Config changes**: Already done (i2c_arm=on)
