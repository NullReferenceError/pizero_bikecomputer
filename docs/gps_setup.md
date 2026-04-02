# GPS Setup Guide

This guide covers setting up GPS modules with pizero_bikecomputer on Raspberry Pi.

## Tested Hardware

- **Sparkfun Max M10S** - u-blox MAX-M10S GPS module
- Connected via UART (GPIO 14/15)

## UART Connection

### Wiring (Crossover Required!)

| GPS Module | → | Raspberry Pi |
|------------|---|--------------|
| **TX** (Transmit) | → | **RX** (GPIO 15 / Pin 10) |
| **RX** (Receive) | → | **TX** (GPIO 14 / Pin 8) |
| **VCC** | → | 3.3V (Pin 1 or 17) |
| **GND** | → | GND (Pin 6, 9, 14, 20, 25, 30, 34, 39) |

**IMPORTANT:** TX→RX and RX→TX (crossover wiring)
- GPS TX sends data → Pi RX receives it
- Pi TX sends data → GPS RX receives it

### UART Configuration

The Raspberry Pi has two UARTs:
1. **PL011 UART** (ttyAMA0) - Full-featured, reliable, recommended for GPS
2. **Mini UART** (ttyS0) - Limited features, not recommended for GPS

By default, Bluetooth uses the PL011 UART. To use it for GPS:

**1. Disable Bluetooth to free PL011 UART:**

Edit `/boot/firmware/config.txt` (or `/boot/config.txt` on older systems):
```bash
# Add this line:
dtoverlay=disable-bt
```

**2. Enable UART:**
```bash
enable_uart=1
```

**3. Disable Bluetooth service:**
```bash
sudo systemctl disable bluetooth
sudo systemctl disable hciuart  # May not exist on all systems
```

**4. Reboot:**
```bash
sudo reboot
```

After reboot:
- `/dev/serial0` → `/dev/ttyAMA0` (PL011 UART)
- Bluetooth will be disabled
- GPS can use the reliable PL011 UART

## GPSD Configuration

pizero_bikecomputer uses **gpsd** to communicate with GPS modules.

### Install GPSD

```bash
sudo apt install gpsd gpsd-clients python3-gps
```

### Configure GPSD

Edit `/etc/default/gpsd`:

```bash
START_DAEMON="true"
GPSD_OPTIONS="-n"
DEVICES="/dev/serial0"
GPSD_SOCKET="/var/run/gpsd.sock"
```

**Key settings:**
- `DEVICES="/dev/serial0"` - Use serial0 (links to the active UART)
- `-n` option - Start immediately, don't wait for client

### Start GPSD

```bash
sudo systemctl enable gpsd
sudo systemctl start gpsd
```

## Testing GPS

### Check UART Devices

```bash
ls -la /dev/serial0 /dev/ttyAMA* /dev/ttyS0
```

Expected output after disabling Bluetooth:
```
lrwxrwxrwx 1 root root 7 /dev/serial0 -> ttyAMA0
crw-rw---- 1 root dialout 204, 64 /dev/ttyAMA0
crw-rw---- 1 root dialout 4, 64 /dev/ttyS0
```

### Test Raw Serial Data

Stop gpsd temporarily:
```bash
sudo systemctl stop gpsd
```

Read raw NMEA sentences:
```bash
stty -F /dev/serial0 speed 9600 -icanon
cat /dev/serial0
```

Expected output (with antenna attached and clear sky view):
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,47.0,M,,*47
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
$GPGSV,3,1,12,01,50,000,47,03,23,295,38,06,31,232,42,09,43,135,41*7F
```

**Without antenna:** You may see no output or partial sentences

Restart gpsd:
```bash
sudo systemctl start gpsd
```

### Test GPSD Connection

```bash
python3 << 'EOF'
import gps
import time

client = gps.gps(mode=gps.WATCH_ENABLE)
print("Checking for GPS data...")

for i in range(10):
    report = client.next()
    report_class = report.get('class', '?')
    print(f"Received: {report_class}")
    
    if report_class == 'TPV':
        print(f"  Lat: {report.get('lat', 'N/A')}")
        print(f"  Lon: {report.get('lon', 'N/A')}")
        print(f"  Mode: {report.get('mode', '?')} (1=no fix, 2=2D, 3=3D)")
        break
    elif report_class == 'SKY':
        sats = report.get('satellites', [])
        print(f"  Satellites visible: {len(sats)}")
        if sats:
            used = sum(1 for s in sats if s.get('used', False))
            print(f"  Satellites used in fix: {used}")
        break
EOF
```

**Expected without antenna:**
- `SKY` reports with 0 satellites
- `TPV` reports with mode=1 (no fix)

**Expected with antenna and sky view:**
- `SKY` reports with 4+ satellites visible
- `TPV` reports with mode=2 or 3 (2D or 3D fix)
- Valid lat/lon coordinates

### Using cgps (Visual Tool)

```bash
cgps -s
```

Shows real-time GPS status with satellite view.

Press `q` to quit.

## Troubleshooting

### No GPS Data

**1. Check UART is enabled:**
```bash
grep enable_uart /boot/firmware/config.txt
# Should show: enable_uart=1
```

**2. Check Bluetooth is disabled:**
```bash
grep disable-bt /boot/firmware/config.txt
# Should show: dtoverlay=disable-bt
```

**3. Check serial0 symlink:**
```bash
ls -la /dev/serial0
# Should point to ttyAMA0, NOT ttyS0
```

**4. Check wiring:**
- TX → RX crossover (NOT TX → TX!)
- 3.3V power (NOT 5V!)
- Good ground connection

**5. Check gpsd is running:**
```bash
systemctl status gpsd
```

**6. Check for permission issues:**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Gibberish Data

If you see garbled characters on the serial port:

**Try different baud rates:**
```bash
# Common GPS baud rates: 9600, 38400, 115200
stty -F /dev/serial0 speed 38400 -icanon
cat /dev/serial0
```

Most GPS modules default to 9600 baud, but check your module's datasheet.

### No Satellites Visible

**1. Check antenna:**
- Antenna must be connected
- Active antennas need power (usually provided by GPS module)
- Passive antennas are simpler but have shorter range

**2. Check location:**
- Need clear view of sky
- Indoors typically won't work
- Near windows may work but is unreliable
- Outdoors is best

**3. Wait for cold start:**
- First fix can take 30-60 seconds (or longer)
- Subsequent fixes are faster (warm start)

**4. Check for interference:**
- Metal cases can block signals
- Wi-Fi/Bluetooth can cause interference (disable-bt helps)
- Keep antenna away from Pi's circuitry

### PPS (Pulse Per Second) Not Working

**PPS requires:**
1. GPS module with PPS output
2. Valid satellite fix (3D fix with time)
3. PPS pin connected to GPIO (typically GPIO 18)
4. PPS kernel module loaded

**Note:** pizero_bikecomputer doesn't require PPS for basic GPS functionality.

## Common GPS Modules

### u-blox Modules (MAX-M10S, NEO-M8N, etc.)

**Default settings:**
- Baud rate: 9600
- Update rate: 1 Hz
- NMEA output enabled

**Configuration:**
- Can be configured via u-center software (Windows)
- Or using UBX protocol commands

### MediaTek Modules (MT3333, etc.)

**Default settings:**
- Baud rate: 9600 or 38400
- Update rate: 1 Hz

**Configuration:**
- Uses PMTK commands via serial
- Example: Set 5Hz update: `$PMTK220,200*2C`

## GPS Performance Tips

### Faster Fix Times

1. **Use A-GPS (Assisted GPS):**
   - Download almanac/ephemeris data
   - Reduces cold start time from 60s to 10s
   - Requires internet connection

2. **Keep GPS powered:**
   - Warm starts are much faster
   - Consider backup battery for GPS module

3. **Good antenna placement:**
   - Clear view of sky
   - Away from metal/interference
   - Horizontal orientation (patch antennas)

### Better Accuracy

1. **Use external active antenna:**
   - Better signal reception
   - Longer cable runs possible

2. **Enable SBAS (WAAS/EGNOS):**
   - Improves accuracy to ~3m
   - Most modules support this

3. **Multi-constellation:**
   - GPS + GLONASS + Galileo + BeiDou
   - More satellites = better fix

## pizero_bikecomputer Integration

### Configuration

GPS settings in `setting.conf`:

```ini
[GPSD_PARAM]
epx_epy_cutoff = 100.0    # Horizontal accuracy threshold (meters)
epv_cutoff = 100.0         # Vertical accuracy threshold (meters)
sp1_epv_cutoff = 100.0     # Single satellite mode threshold
sp1_used_sats_cutoff = 3   # Minimum satellites for valid fix
```

### How It Works

1. **GPS Module** → sends NMEA sentences via UART
2. **gpsd** → parses NMEA and provides standardized API
3. **pizero_bikecomputer** → reads from gpsd via Python gps library
4. **Display** → shows speed, distance, location, etc.

### Startup Sequence

1. System boots
2. gpsd service starts automatically
3. pizero_bikecomputer service starts
4. GPS sensor initializes (modules/sensor/sensor_gps.py)
5. Waits for valid GPS fix
6. Displays GPS data on screen

## See Also

- [GPSD Documentation](https://gpsd.io/)
- [u-blox Protocol Specifications](https://www.u-blox.com/en/product-resources)
- [NMEA 0183 Standard](https://en.wikipedia.org/wiki/NMEA_0183)
- [Raspberry Pi UART Documentation](https://www.raspberrypi.com/documentation/computers/configuration.html#configure-uarts)

## Related Files

- `/boot/firmware/config.txt` - UART and Bluetooth configuration
- `/etc/default/gpsd` - GPSD daemon configuration  
- `modules/sensor/sensor_gps.py` - GPS sensor implementation
- `modules/helper/setting.py` - Configuration loading

## Contributing

If you successfully set up a different GPS module, please update this documentation with:
- Module model and specifications
- Any special wiring or configuration needed
- Photos of the setup (optional)

Submit via pull request to the main repository.
