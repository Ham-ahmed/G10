#!/bin/bash

##setup command=wget -q "--no-check-certificate" https://raw.githubusercontent.com/Ham-ahmed/G10/refs/heads/main/MagicPanelGold-install.sh -O - | /bin/sh

######### Only This line to edit with new version ######
version='10.0'
##############################################################

TMPPATH=/tmp/MagicPanelGold
GITHUB_BASE="https://raw.githubusercontent.com/Ham-ahmed/G10/refs/heads/main"
GITHUB_RAW="${GITHUB_BASE}"

# Check architecture and set plugin path
if [ ! -d /usr/lib64 ]; then
    PLUGINPATH="/usr/lib/enigma2/python/Plugins/Extensions/MagicPanelGold"
else
    PLUGINPATH="/usr/lib64/enigma2/python/Plugins/Extensions/MagicPanelGold"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to restart Enigma2 safely
restart_enigma2() {
    print_message $YELLOW "> Restarting Enigma2..."
    sleep 2
    
    if command_exists systemctl; then
        systemctl restart enigma2
    elif command_exists init; then
        init 4
        sleep 2
        init 3
    else
        killall -9 enigma2
        sleep 2
        if command_exists enigma2; then
            enigma2 >/dev/null 2>&1 &
        fi
    fi
    sleep 3
}

# Function to install package with error handling
install_package() {
    local package=$1
    local package_name=$2
    
    print_message $BLUE "> Installing $package_name..."
    
    if [ "$OSTYPE" = "DreamOs" ]; then
        if command_exists apt-get; then
            apt-get update >/dev/null 2>&1 && apt-get install "$package" -y >/dev/null 2>&1
            return $?
        else
            print_message $RED "> apt-get not found!"
            return 1
        fi
    else
        if command_exists opkg; then
            opkg update >/dev/null 2>&1 && opkg install "$package" >/dev/null 2>&1
            return $?
        else
            print_message $RED "> opkg not found!"
            return 1
        fi
    fi
}

# Function to check package status
check_package() {
    local package=$1
    if [ -f /var/lib/dpkg/status ]; then
        grep -qs "Package: $package" /var/lib/dpkg/status
    elif [ -f /var/lib/opkg/status ]; then
        grep -qs "Package: $package" /var/lib/opkg/status
    else
        return 1
    fi
}

# Detect OS type and package manager status
if [ -f /var/lib/dpkg/status ]; then
    STATUS="/var/lib/dpkg/status"
    OSTYPE="DreamOs"
else
    STATUS="/var/lib/opkg/status"
    OSTYPE="Dream"
fi

# Clear screen and show banner
clear
echo ""
print_message $CYAN "======================================================"
print_message $YELLOW "           MagicPanelGold Installer v$version"
print_message $CYAN "======================================================"
echo ""

# Detect Python version
PYTHON="PY2"
Packagesix=""
Packagerequests="python-requests"

if command -v python3 >/dev/null 2>&1; then
    print_message $GREEN "> You have Python3 image"
    PYTHON="PY3"
    Packagesix="python3-six"
    Packagerequests="python3-requests"
elif command -v python2 >/dev/null 2>&1; then
    print_message $GREEN "> You have Python2 image"
    PYTHON="PY2"
    Packagerequests="python-requests"
elif command -v python >/dev/null 2>&1; then
    if python --version 2>&1 | grep -q '^Python 3\.'; then
        print_message $GREEN "> You have Python3 image"
        PYTHON="PY3"
        Packagesix="python3-six"
        Packagerequests="python3-requests"
    else
        print_message $GREEN "> You have Python2 image"
        PYTHON="PY2"
        Packagerequests="python-requests"
    fi
else
    print_message $RED "> Python not found! Please install Python first."
    exit 1
fi

# Install required packages
echo ""
print_message $BLUE "> Checking required packages..."

if [ "$PYTHON" = "PY3" ] && [ ! -z "$Packagesix" ]; then
    if ! check_package "$Packagesix"; then
        print_message $YELLOW "> Required package $Packagesix not found, installing..."
        if ! install_package "$Packagesix" "python3-six"; then
            print_message $YELLOW "> Failed to install $Packagesix, continuing without it..."
        fi
    fi
fi

echo ""
if ! check_package "$Packagerequests"; then
    print_message $YELLOW "> $Packagerequests must be installed"
    if ! install_package "$Packagerequests" "python-requests"; then
        print_message $RED "> Failed to install $Packagerequests"
        exit 1
    fi
fi

echo ""

# Cleanup previous installations
print_message $BLUE "> Cleaning previous installations..."
[ -d "$TMPPATH" ] && rm -rf "$TMPPATH" > /dev/null 2>&1
[ -d "$PLUGINPATH" ] && rm -rf "$PLUGINPATH" > /dev/null 2>&1

# Download and install plugin
print_message $BLUE "> Downloading MagicPanelGold v$version..."
mkdir -p "$TMPPATH"
cd "$TMPPATH" || exit 1

# Detect OE version
if [ -f /var/lib/dpkg/status ]; then
    print_message $GREEN "# Your image is OE2.5/2.6 #"
else
    print_message $GREEN "# Your image is OE2.0 #"
fi

echo ""

# Download the plugin with corrected URL structure
print_message $BLUE "> Downloading from GitHub..."
DOWNLOAD_URL="${GITHUB_BASE}/MagicPanelGold_v${version}.tar.gz"

if ! wget -q --no-check-certificate --timeout=30 --tries=3 "$DOWNLOAD_URL" -O "MagicPanelGold_v${version}.tar.gz"; then
    print_message $RED "> Download failed from: $DOWNLOAD_URL"
    exit 1
fi

# Check if file was downloaded
if [ ! -f "MagicPanelGold_v${version}.tar.gz" ]; then
    print_message $RED "> Download file doesn't exist!"
    exit 1
fi

# Extract the plugin
print_message $BLUE "> Extracting files..."
if ! tar -xzf "MagicPanelGold_v${version}.tar.gz" 2>/dev/null; then
    print_message $RED "> Failed to extract files!"
    exit 1
fi

# Install the plugin (Improved copy logic)
print_message $BLUE "> Installing plugin..."
mkdir -p "$PLUGINPATH"

# Find all files and copy them maintaining structure
find . -type f \( -name "*.py" -o -name "*.pyo" -o -name "*.pyc" -o -name "*.so" -o -name "*.png" -o -name "*.xml" -o -name "*.json" -o -name "*.txt" -o -name "*.po" -o -name "*.mo" \) | while read -r file; do
    # Remove leading './'
    clean_file="${file#./}"
    dest_dir="$PLUGINPATH/$(dirname "$clean_file")"
    mkdir -p "$dest_dir"
    cp -f "$file" "$dest_dir/" 2>/dev/null
done

# Copy locale directory if it exists
if [ -d "locale" ]; then
    cp -rf locale/* "$PLUGINPATH/../" 2>/dev/null
fi

# Verify installation
print_message $BLUE "> Verifying installation..."
if [ ! -d "$PLUGINPATH" ] || [ -z "$(ls -A "$PLUGINPATH" 2>/dev/null)" ]; then
    print_message $RED "> Installation failed! Could not copy plugin files."
    exit 1
fi

# Set correct permissions
print_message $BLUE "> Setting file permissions..."
find "$PLUGINPATH" -type f -name "*.py" -exec chmod 644 {} \; 2>/dev/null
find "$PLUGINPATH" -type f -name "*.pyo" -exec chmod 644 {} \; 2>/dev/null
find "$PLUGINPATH" -type f -name "*.so" -exec chmod 755 {} \; 2>/dev/null
find "$PLUGINPATH" -type d -exec chmod 755 {} \; 2>/dev/null

# Cleanup
print_message $BLUE "> Cleaning temporary files..."
rm -rf "$TMPPATH" > /dev/null 2>&1
sync

# Success message
echo ""
print_message $CYAN "==================================================================="
print_message $GREEN "===              Installation Successful!                       ==="
printf "${YELLOW}===                 MagicPanelGold v%-24s===${NC}\n" "$version"
print_message $BLUE "===              Downloaded by  >>>>   HAMDY_AHMED               ==="
print_message $CYAN "==================================================================="
echo ""
print_message $YELLOW "Enigma2 will restart automatically after 5 seconds..."
print_message $BLUE "Press Ctrl+C to cancel"
echo ""

# Countdown before restart
for i in {5..1}; do
    printf "${YELLOW}Restarting in $i seconds...${NC}\r"
    sleep 1
done
echo ""

# Automatic restart
print_message $GREEN "========================================================="
print_message $YELLOW "===            Restarting Enigma2                     ==="
print_message $GREEN "========================================================="

restart_enigma2

exit 0