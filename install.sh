#!/bin/bash
set -euo pipefail
#############################################################
# This script sets up pizero_bikecomputer environment
# and is intended to be run on a fresh Raspberry Pi OS installation.
# 1. Creates a Python virtual environment, installs necessary
#    packages, and prepares the system for running pizero_bikecomputer
#    application.
# 2. Be aware that this script will not install pizero_bikecomputer_service
#    and it will not install sensor specific packages.
# 3. It is intended to be run once, before pizero_bikecomputer_service
#    is installed.
#
# This script is based on the instructions from the pizero_bikecomputer
# foud here: https://qiita.com/hishi/items/46619b271daaa9ad41b3
#
# Usage: ./scripts/initial_setup.sh
#
#############################################################

###
# Function to ask user for input
# Returns "true" for yes, "false" for no, and exits for quit.
###
ask_user() {
    local prompt="$1"
    while true; do
        read -rp "$prompt [y/n/q(uit)]: " answer
        #answer="${answer,,}"  # lowercase
        answer="$(echo "$answer" | tr 'A-Z' 'a-z')"

        case "$answer" in
            y|yes) return 0 ;;
            n|no) return 1 ;;
            q|quit) return 2 ;;
            *) echo "Invalid input. Please answer with y, n, or q." ;;
        esac
    done
}

prompt_and_store() {
    local prompt="$1"
    local var_name="$2"
    if [[ "$auto_yes" == "true" ]]; then
        eval "$var_name=true"
        return 0
    fi
    ask_user "$prompt"
    case $? in
        0) eval "$var_name=true" ;;
        1) eval "$var_name=false" ;;
        2) echo "👋 Quitting...bye!"; exit 0 ;;
    esac
}

install_timezonefinder_and_flatbuffers() {
    if [[ "${INSTALL_TZ_DEPS_DONE:-false}" == "true" ]]; then
        return 0
    fi
    local pip_tmp_dir
    pip_tmp_dir="$HOME/tmp/pip"
    mkdir -p "$pip_tmp_dir"
    TMPDIR="$pip_tmp_dir" pip install timezonefinder
    rm -rf "$pip_tmp_dir"
    # Force PyPI to avoid legacy versions from extra index settings.
    pip uninstall -y flatbuffers
    PIP_CONFIG_FILE=/dev/null pip install -U --no-cache-dir -i https://pypi.org/simple flatbuffers
    INSTALL_TZ_DEPS_DONE=true
}

check_sharp_drm() {
    KERNEL_MAJOR=$(uname -r | cut -d'.' -f1)
    KERNEL_MINOR=$(uname -r | cut -d'.' -f2 | cut -d'+' -f1)
    
    if [ "$KERNEL_MAJOR" -ge 6 ] && [ "$KERNEL_MINOR" -ge 12 ]; then
        echo "⚠️  Kernel 6.12+ detected - sharp-drm not recommended"
        echo "   Use pigpio backend instead:"
        echo "   - Set USE_DRM = False in setting.conf"
        echo "   - Ensure pigpiod is running"
        echo "   - Set display = MIP_Sharp_mono_400x240"
        return 3
    fi
    
    if [ -d "/sys/module/sharp_drm" ]; then
        if [ -e "/dev/fb1" ]; then
            return 0
        fi
        if [ -e "/dev/dri/card0" ]; then
            return 0
        fi
        echo "⚠️ sharp_drm module loaded but no display device"
        return 1
    fi

    if lsmod 2>/dev/null | grep -q "^sharp_drm"; then
        if [ -e "/dev/fb1" ]; then
            return 0
        fi
        if [ -e "/dev/dri/card0" ]; then
            return 0
        fi
        echo "⚠️ sharp_drm module loaded but no display device"
        return 1
    fi

    if command -v modinfo >/dev/null 2>&1 && modinfo sharp_drm >/dev/null 2>&1; then
        echo "⚠️ sharp_drm module available but not loaded"
        echo "   On kernel 6.12+, use pigpio instead"
        return 2
    fi

    return 3
}

install_sharp_drm() {
    KERNEL_MAJOR=$(uname -r | cut -d'.' -f1)
    KERNEL_MINOR=$(uname -r | cut -d'.' -f2 | cut -d'+' -f1)
    
    if [ "$KERNEL_MAJOR" -ge 6 ] && [ "$KERNEL_MINOR" -ge 12 ]; then
        echo "⚠️  sharp-drm not supported on kernel 6.12+"
        echo ""
        echo "   Use pigpio backend instead:"
        echo "   1. Edit setting.conf and add:"
        echo "      [DISPLAY]"
        echo "      USE_DRM = False"
        echo "   2. Or set in [GENERAL]: display = MIP_Sharp_mono_400x240"
        echo "   3. Ensure pigpiod is running:"
        echo "      sudo systemctl enable pigpiod"
        echo "      sudo systemctl start pigpiod"
        return 0
    fi
    
    echo "🔧 Installing sharp_drm kernel module for SHARP MIP display..."
    
    if [ -d "/sys/module/sharp_drm" ] && [ -e "/dev/fb1" ]; then
        echo "✅ sharp_drm already installed and loaded"
        return 0
    fi

    echo "📦 Checking kernel headers..."
    if [ ! -d "/lib/modules/$(uname -r)/build" ]; then
        echo "📦 Installing kernel headers..."
        sudo apt update
        if apt-cache show raspberrypi-kernel-headers >/dev/null 2>&1; then
            sudo apt install -y raspberrypi-kernel-headers
        else
            sudo apt install -y linux-headers-$(uname -r | cut -d'+' -f1)-arm64
        fi
    else
        echo "✅ Kernel headers already available"
    fi

    if ! command -v git >/dev/null 2>&1; then
        sudo apt install -y git
    fi
    if ! command -v make >/dev/null 2>&1; then
        sudo apt install -y make
    fi

    local sharp_driversrc="$HOME/sharp-drm-driver"
    if [ -d "$sharp_driversrc" ]; then
        echo "📦 Updating existing sharp-drm-driver..."
        cd "$sharp_driversrc"
        git pull
    else
        echo "📦 Cloning sharp-drm-driver..."
        git clone https://github.com/ardangelo/sharp-drm-driver.git "$sharp_driversrc"
        cd "$sharp_driversrc"
    fi

    echo "🔨 Building sharp_drm module..."
    make

    echo "📦 Installing sharp_drm module..."
    sudo make install

    echo "🔄 Loading sharp_drm module..."
    sudo modprobe sharp_drm

    echo "🔄 Loading device tree overlay..."
    sudo dtoverlay sharp-drm

    if [ -e "/dev/dri/card0" ] || [ -e "/dev/fb1" ]; then
        echo "✅ sharp_drm installed successfully!"
        echo "   Device: $([ -e /dev/dri/card0 ] && echo /dev/dri/card0 || echo /dev/fb1)"
        return 0
    else
        echo "⚠️ sharp_drm installed but no display device found"
        echo "   Try rebooting: sudo reboot"
        return 1
    fi
}

#############################################################
# argument parsing
#############################################################

show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    --venv              Setup Python virtual environment (default: yes)
    --venv-name NAME    Virtual environment name (default: .venv)
    --no-venv           Skip virtual environment setup
    --pyqt6             Install PyQt6 packages (default: yes)
    --no-pyqt6          Skip PyQt6 packages
    --ant               Install ANT+ packages
    --no-ant            Skip ANT+ packages (default)
    --gps               Install GPS packages
    --no-gps            Skip GPS packages (default)
    --bluetooth         Install Bluetooth packages
    --no-bluetooth      Skip Bluetooth packages (default)
    --i2c               Enable I2C
    --spi               Enable SPI
    --services          Install systemd services
    --xwindow           Use X11 instead of framebuffer for services
    --sharp-drm         Auto-install sharp_drm kernel module
    -y, --yes           Answer yes to all prompts
    -h, --help          Show this help message

Examples:
    $0 --pyqt6 --spi --services --sharp-drm
    $0 -y  # non-interactive with defaults
EOF
    exit 0
}

setup_python_venv="true"
venv_name=".venv"
install_pyqt6="true"
install_ant_plus="false"
install_gps="false"
install_bluetooth="false"
enable_i2c="false"
enable_spi="false"
install_services="false"
install_services_use_x="false"
install_sharp_drm_auto="false"
auto_yes="false"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --venv)           setup_python_venv="true" ;;
        --venv-name)      venv_name="$2"; shift ;;
        --no-venv)        setup_python_venv="false" ;;
        --pyqt6)          install_pyqt6="true" ;;
        --no-pyqt6)       install_pyqt6="false" ;;
        --ant)            install_ant_plus="true" ;;
        --no-ant)         install_ant_plus="false" ;;
        --gps)            install_gps="true" ;;
        --no-gps)         install_gps="false" ;;
        --bluetooth)      install_bluetooth="true" ;;
        --no-bluetooth)   install_bluetooth="false" ;;
        --i2c)            enable_i2c="true" ;;
        --spi)            enable_spi="true" ;;
        --services)       install_services="true" ;;
        --xwindow)        install_services="true"; install_services_use_x="true" ;;
        --sharp-drm)      install_sharp_drm_auto="true" ;;
        -y|--yes)         auto_yes="true" ;;
        -h|--help)        show_usage ;;
        *) echo "Unknown option: $1"; show_usage ;;
    esac
    shift
done

TARGET_USER="${SUDO_USER:-${LOGNAME:-$USER}}"
venv_path=~/"$venv_name"

#############################################################
# get user input (interactive mode)
#############################################################

if [[ "$auto_yes" != "true" ]]; then
    set +e
    prompt_and_store "Setup Python virtual environment?" setup_python_venv
    if [[ "$setup_python_venv" == "true" ]]; then
        read -rp "📦 Enter virtual environment name (default: .venv): " venv_name
        venv_name="${venv_name:-.venv}"
        venv_path=~/"$venv_name"
    fi
    prompt_and_store "Install GUI(PyQt6) packages?" install_pyqt6
    prompt_and_store "Install ANT+ packages?" install_ant_plus
    prompt_and_store "Install GPS packages?" install_gps
    prompt_and_store "Install Bluetooth packages?" install_bluetooth
    prompt_and_store "Enable I2C?" enable_i2c
    prompt_and_store "Enable SPI?" enable_spi
    prompt_and_store "Install services?" install_services
    if [[ "$install_services" == "true" ]]; then
        prompt_and_store "Using TFT/XWindow to start pizero_bikecomputer.service?" install_services_use_x
    fi
    set -e
fi

#############################################################
# install packages
#############################################################

TARGET_USER="${SUDO_USER:-${LOGNAME:-$USER}}"

# system update
sudo apt update
sudo apt upgrade -y

# install essential packages
echo "🔧 Installing core packages..."
# trixie
sudo apt install -y git cython3 cmake python3-setuptools python3.13-venv python3-numpy sqlite3 libsqlite3-dev python3-pil python3-aiohttp python3-psutil
echo "✅ Core packages installed."

cd

# setup virutal environment
if [[ "$setup_python_venv" == "true" ]]; then
    echo "🔧 Creating virtual environment at: $venv_path"
    python3 -m venv --system-site-packages "$venv_path"
    if ! grep -Fxq "source $venv_path/bin/activate" ~/.bashrc; then
        echo "source $venv_path/bin/activate" >> ~/.bashrc
        echo "🔧 Added 'source $venv_path/bin/activate' to ~/.bashrc"
    fi
    source "$venv_path/bin/activate"
    echo "✅ Virtual environment setup complete. Python location: $(which python3), pip location: $(which pip3)"
else
    echo "⏭️ Skipping Python virtual environment setup."
fi

# Install additional requirements
echo "🔧 Installing core pip packages..."
# essential
pip install --break-system-packages oyaml polyline
echo "✅ Core pip packages installed successfully."

if command -v raspi-config >/dev/null 2>&1; then
    has_raspi_config=true
else
    has_raspi_config=false
fi

# Install PyQt6 packages
if [[ "$install_pyqt6" == "true" ]]; then
    echo "🔧 Installing PyQt6 packages..."
    sudo apt install -y python3-pyqt6 python3-pyqt6.qtsvg qt6-svg-plugins pyqt6-dev-tools
    pip install --break-system-packages qasync pyqtgraph
    # sudo apt install -y python3-pyside6.qtlocation
    echo "✅ PyQt6 packages installed successfully."
    gui_option=()
else
    gui_option=(--gui None)
fi

# Install ANT+ packages
if [[ "$install_ant_plus" == "true" ]]; then
    echo "🔧 Installing ANT+ packages..."
    # trixie
    sudo apt install -y python3-pip python3-usb
    # install as root to ensure there are no udev_rules permission issues from setuptools
    sudo pip3 install git+https://github.com/hishizuka/openant.git --break-system-packages
    echo "✅ ANT+ packages installed successfully."
fi

# Install GPS packages
if [[ "$install_gps" == "true" ]]; then
    echo "🔧 Installing GPS packages..."
    # trixie
    sudo apt install -y gpsd python3-gps libffi-dev
    install_timezonefinder_and_flatbuffers

    if [[ "$has_raspi_config" == "true" ]]; then
        sudo raspi-config nonint do_serial_cons 1
        sudo raspi-config nonint do_serial_hw 0
    fi
    sudo systemctl enable gpsd
    sudo systemctl enable gpsd.socket
    echo "✅ GPS packages installed successfully."
fi

# Install Bluetooth packages
if [[ "$install_bluetooth" == "true" ]]; then
    echo "🔧 Installing Bluetooth packages..."
    # for trixie
    sudo usermod -aG bluetooth "$TARGET_USER"
    sudo rfkill unblock bluetooth
    # install packages
    sudo apt install -y bluez-obexd libffi-dev
    # for raspberry pi zero (building with pip is extremely heavy.)
    sudo apt install -y python3-pydantic python3-orjson
    pip install --break-system-packages garminconnect stravacookies bluez-peripheral==0.2.0a5 tb-mqtt-client mmh3
    install_timezonefinder_and_flatbuffers

    echo "✅ Bluetooth packages installed successfully."
fi

# Enable I2C
if [[ "$enable_i2c" == "true" ]]; then
    sudo apt install -y python3-smbus2 libgpiod3 libgpiod-dev python3-libgpiod
    pip install --break-system-packages magnetic-field-calculator
    # Enable I2C on Raspberry Pi
    echo "🔧 Enabling i2c on Raspberry Pi..."
    if [[ "$has_raspi_config" == "true" ]]; then
        sudo raspi-config nonint do_i2c 0
    fi
    # add pi to i2c if not already a member
    #if ! groups "$TARGET_USER" | grep -qw i2c; then
    #  sudo adduser "$TARGET_USER" i2c
    #fi
    echo "✅ I2C enabled successfully"
fi

# Enable SPI
if [[ "$enable_spi" == "true" ]]; then
sudo apt install -y libgpiod3 libgpiod-dev python3-libgpiod
    # Enable SPI on Raspberry Pi
    echo "🔧 Enabling spi on Raspberry Pi..."
    if [[ "$has_raspi_config" == "true" ]]; then
        sudo raspi-config nonint do_spi 0
    fi
    # add pi to i2c if not already a member
    #if ! groups "$TARGET_USER" | grep -qw spi; then
    #  sudo adduser "$TARGET_USER" spi
    #fi
    
    # pigpio for trixie (To be deprecated)
    # sudo apt install -y pigpio python3-pigpio
    # or manually install
    
    # sudo systemctl enable pigpiod
    #echo "ℹ️ pigpio enabled  successfully."

    echo "✅ SPI enabled successfully"
fi

#############################################################
# disable raspberry pi specific hardware
#############################################################

BOOT_CONFIG_FILE="/boot/firmware/config.txt"

# Disable audio on Raspberry Pi
if [ -f "$BOOT_CONFIG_FILE" ]; then
    AUDIO_PARAM="dtparam=audio=on"
    # Disable audio on Raspberry Pi
    echo "🔧 Disabling the Raspberry Pi audio..."
    if grep -q "^[^#]*$AUDIO_PARAM" "$BOOT_CONFIG_FILE"; then
        sudo sed -i "/^[^#]*$AUDIO_PARAM/s/^/#/" "$BOOT_CONFIG_FILE"
    else
        echo "ℹ️ Audio is already disabled or line is commented out."
    fi
    echo "✅ Audio disabled successfully in $BOOT_CONFIG_FILE (or already disabled)"
fi

# Disable LED
if [ -f "$BOOT_CONFIG_FILE" ]; then
    # Append LED trigger settings if missing to keep LEDs off during normal operation
    if ! grep -q "^dtparam=pwr_led_trigger=none" "$BOOT_CONFIG_FILE"; then
        echo "dtparam=pwr_led_trigger=none" | sudo tee -a "$BOOT_CONFIG_FILE" >/dev/null
    fi
    if ! grep -q "^dtparam=act_led_trigger=none" "$BOOT_CONFIG_FILE"; then
        echo "dtparam=act_led_trigger=none" | sudo tee -a "$BOOT_CONFIG_FILE" >/dev/null
    fi
fi

# Disable camera on Raspberry Pi
if [[ "$has_raspi_config" == "true" ]]; then
    echo "🔧 Disabling Raspberry Pi camera..."
    sudo raspi-config nonint do_camera 1
fi

#############################################################
# test run
#############################################################

echo "🔧 Starting pizero_bikecomputer.py for initialize..."
pgm_dir=~/pizero_bikecomputer
if [ ! -d "$pgm_dir" ]; then
    git clone https://github.com/hishizuka/pizero_bikecomputer.git
fi

cd "$pgm_dir"

# Create a named pipe (FIFO) to monitor output
OUT_PIPE=$(mktemp -u)
mkfifo "$OUT_PIPE"

cleanup() {
    rm -f "$OUT_PIPE"
    kill "$APP_PID" 2>/dev/null || true
}
trap cleanup EXIT

# Start the app and tee its output to both screen and PIPE
export QT_QPA_PLATFORM=offscreen
stdbuf -oL python3 pizero_bikecomputer.py --init "${gui_option[@]}" 2>&1 | tee "$OUT_PIPE" &
APP_PID=$!

# Monitor the output for readiness
ready=0
while IFS= read -r line; do
    if [ "$ready" -eq 0 ]; then
        case "$line" in
            quit)
                echo "ℹ️ 'quit' detected. Waiting 10s..."
                ready=1
            ;;
        esac
    fi

    if [ "$ready" -eq 1 ]; then
        case "$line" in
            *"quit done"*)
                echo "✅ 'quit done' detected. Stopping app..."
                kill "$APP_PID" 2>/dev/null || true
                wait "$APP_PID" 2>/dev/null || true
                break
            ;;
        esac
    fi
done < "$OUT_PIPE"

# check setting.conf
if [ -f setting.conf ]; then
    echo "✅ Startup test completed successfully."
else
    echo "❌ Application did not start correctly. Check logs or errors."
fi

#############################################################
# Install Services
#############################################################

if [[ "$install_services" == "true" ]]; then

    echo "🔍 Checking for SHARP MIP display and sharp_drm kernel module..."
    sharp_drm_loaded="false"
    check_sharp_drm
    sharp_drm_status=$?
    case $sharp_drm_status in
        0)
            if [ -e "/dev/fb1" ]; then
                echo "✅ sharp_drm kernel module detected with /dev/fb1 available"
            else
                echo "✅ sharp_drm kernel module detected with /dev/dri/card0 (kernel 6.12+)"
            fi
            sharp_drm_loaded="true"
            ;;
        1|2|3)
            if [[ "$install_sharp_drm_auto" == "true" ]]; then
                echo "🔧 Auto-installing sharp_drm (--sharp-drm specified)..."
                if install_sharp_drm; then
                    sharp_drm_loaded="true"
                else
                    echo "⚠️  sharp_drm install completed but /dev/fb1 not found"
                    echo "   You may need to reboot: sudo reboot"
                fi
            else
                echo ""
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo "⚠️  SHARP MIP display detected but sharp_drm module needs setup"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                echo ""
                prompt_and_store "Install sharp_drm kernel module automatically?" install_sharp_drm_prompt
                if [[ "$install_sharp_drm_prompt" == "true" ]]; then
                    if install_sharp_drm; then
                        sharp_drm_loaded="true"
                    else
                        echo "⚠️  sharp_drm install completed but /dev/fb1 not found"
                        echo "   Try rebooting and running install.sh again"
                        prompt_and_store "Continue with offscreen mode for now?" continue_offscreen
                        if [[ "$continue_offscreen" != "true" ]]; then
                            echo "👋 Exiting. Reboot and run install.sh again."
                            exit 0
                        fi
                    fi
                else
                    echo "⚠️  Skipping sharp_drm installation"
                    echo "   For SHARP MIP display, you need:"
                    echo "   1. git clone https://github.com/ardangelo/sharp-drm-driver.git"
                    echo "   2. cd sharp-drm-driver && make && sudo make install"
                    echo "   3. sudo modprobe sharp_drm"
                    echo ""
                    echo "   Then set QT_QPA_PLATFORM=linuxfb:fb=/dev/fb1"
                    prompt_and_store "Continue with offscreen mode for now?" continue_offscreen
                    if [[ "$continue_offscreen" != "true" ]]; then
                        echo "👋 Exiting."
                        exit 0
                    fi
                fi
            fi
            ;;
    esac

    # GPS service configuration
    if [[ "$install_gps" == "true" ]]; then
        sudo cp scripts/install/etc/default/gpsd /etc/default/gpsd
        sudo systemctl start gpsd
    fi

    # Build Cython modules to avoid runtime compilation delays
    echo ""
    echo "🔨 Building Cython modules..."
    if [[ -f "scripts/build_cython.sh" ]]; then
        if bash scripts/build_cython.sh; then
            echo "✅ Cython modules built successfully"
        else
            echo "⚠️  Warning: Cython build failed. Modules will be compiled on first run."
            echo "   This may cause a delay when starting the service."
        fi
    else
        echo "⚠️  Warning: build_cython.sh not found. Skipping Cython build."
    fi

    # install pizero_bikecomputer.service
    current_dir=$(pwd)
    script="$current_dir/pizero_bikecomputer.py"

    i_service_file="scripts/install/etc/systemd/system/pizero_bikecomputer.service"
    o_service_file="/etc/systemd/system/pizero_bikecomputer.service"

    log_file="$current_dir/log/debug.log"
    i_post_exec_file="scripts/install/usr/local/bin/rotate_debug_log.sh"
    o_post_exec_file="/usr/local/bin/rotate_debug_log.sh"

    # check if venv is set, in that case default to using venv to run the script
    #read -p "Use current virtualenv? [y/n] (y): " use_venv
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        script="$VIRTUAL_ENV/bin/python $script"
    else
    echo "No virtualenv used/activated. Default python will be used"
    fi

    if [[ "$install_services_use_x" == "true" ]]; then
        # add fullscreen option
        script="$script -f"
        envs="Environment=\"QT_QPA_PLATFORM=xcb\"\\nEnvironment=\"DISPLAY=:0\"\\nEnvironment=\"XAUTHORITY=/home/$TARGET_USER/.Xauthority\"\\n"
        after="After=display-manager.service\\n"
    else
        envs="Environment=\"QT_QPA_PLATFORM=offscreen\"\\n"
        # DRM
        #envs="Environment=\"QT_QPA_PLATFORM=linuxfb:fb=/dev/fb1\"\\n"
        # PiTFT
        #envs="Environment=\"QT_QPA_FB_HIDECURSOR=1 QT_QPA_PLATFORM=linuxfb:fb=/dev/fb1\"\\n"
        # and add vt.global_cursor_default=0 fbcon=map:0 or 1(map console with /dev/fbX)
        after=""
    fi

    if [ -f "$i_service_file" ]; then
        content=$(<"$i_service_file")
        content="${content/WorkingDirectory=/WorkingDirectory=$current_dir}"
        content="${content/ExecStartPre=/ExecStartPre=$o_post_exec_file}"
        content="${content/ExecStart=/ExecStart=$script}"
        content="${content/ExecStopPost=/ExecStopPost=$o_post_exec_file}"
        content="${content/User=/User=$TARGET_USER}"
        content="${content/Group=/Group=$TARGET_USER}"
        content="${content/StandardOutput=/StandardOutput=append:$log_file}"

        # inject environment variables
        content=$(echo "$content" | sed "/\[Install\]/i $envs")

        if [[ -n "$after" ]]; then
            content=$(echo "$content" | sed "/\[Service\]/i $after")
        fi
        echo "$content" | sudo tee $o_service_file > /dev/null
        sudo systemctl enable pizero_bikecomputer
    fi

    if [ -f "$i_post_exec_file" ]; then
        content=$(<"$i_post_exec_file")
        content="${content/LOG=/LOG=$log_file}"

        echo "$content" | sudo tee $o_post_exec_file > /dev/null
        sudo chown $TARGET_USER:$TARGET_USER $o_post_exec_file
    fi

fi

echo "✅ pizero_bikecomputer initial setup completed successfully!"
echo ""

# Ask user if they want to start the service now or reboot
if [[ "$auto_yes" == "true" ]]; then
    echo "Starting pizero_bikecomputer service..."
    sudo systemctl daemon-reload
    sudo systemctl start pizero_bikecomputer
    echo "✅ Service started. Check status with: systemctl status pizero_bikecomputer"
else
    echo "To complete the setup, you can either:"
    echo "  1. Start the service now: sudo systemctl start pizero_bikecomputer"
    echo "  2. Reboot the system: sudo reboot"
    echo ""
    prompt_and_store "Start the service now?" start_service
    if [[ "$start_service" == "true" ]]; then
        echo "Starting pizero_bikecomputer service..."
        sudo systemctl daemon-reload
        sudo systemctl start pizero_bikecomputer
        echo "✅ Service started. Check status with: systemctl status pizero_bikecomputer"
        echo "   View logs with: tail -f ~/pizero_bikecomputer/log/debug.log"
    else
        echo "👋 Remember to start the service or reboot when ready!"
    fi
fi
