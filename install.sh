#!/bin/bash
# CabinPython v2 Installation Script
# This script installs the daemon as a systemd service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="/opt/cabinpython"
SERVICE_FILE="/etc/systemd/system/cabinpi-daemon.service"
USER="ckent"

echo -e "${GREEN}CabinPython v2 Daemon Installation${NC}"
echo "======================================"
echo

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Error: This script must be run as root${NC}"
    echo "Please run: sudo ./install.sh"
    exit 1
fi

# Check if Python 3.9+ is available
echo -e "${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "Found Python ${PYTHON_VERSION}"

# Create installation directory
echo -e "${YELLOW}Creating installation directory...${NC}"
mkdir -p "${INSTALL_DIR}"

# Copy files
echo -e "${YELLOW}Copying application files...${NC}"
cp -r cabinpi "${INSTALL_DIR}/"
cp daemon.py "${INSTALL_DIR}/"
cp requirements.txt "${INSTALL_DIR}/"
cp config.yaml.example "${INSTALL_DIR}/"
cp .env.example "${INSTALL_DIR}/"
cp README-v2.md "${INSTALL_DIR}/"

# Create config if it doesn't exist
if [ ! -f "${INSTALL_DIR}/config.yaml" ]; then
    echo -e "${YELLOW}Creating default configuration...${NC}"
    cp "${INSTALL_DIR}/config.yaml.example" "${INSTALL_DIR}/config.yaml"
    echo -e "${GREEN}Created config.yaml - PLEASE EDIT THIS FILE${NC}"
fi

if [ ! -f "${INSTALL_DIR}/.env" ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"
    echo -e "${GREEN}Created .env - PLEASE EDIT THIS FILE WITH YOUR SECRETS${NC}"
fi

# Create virtual environment
echo -e "${YELLOW}Creating Python virtual environment...${NC}"
python3 -m venv "${INSTALL_DIR}/env"

# Install dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
"${INSTALL_DIR}/env/bin/pip" install --upgrade pip
"${INSTALL_DIR}/env/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

# Set ownership
echo -e "${YELLOW}Setting file permissions...${NC}"
chown -R ${USER}:${USER} "${INSTALL_DIR}"
chmod +x "${INSTALL_DIR}/daemon.py"

# Add user to required groups for hardware access
echo -e "${YELLOW}Adding user to hardware access groups...${NC}"
usermod -a -G dialout,i2c,gpio ${USER} || true

# Install systemd service
echo -e "${YELLOW}Installing systemd service...${NC}"
cp systemd/cabinpi-daemon.service "${SERVICE_FILE}"

# Reload systemd
systemctl daemon-reload

echo
echo -e "${GREEN}Installation complete!${NC}"
echo
echo "Next steps:"
echo "1. Edit ${INSTALL_DIR}/config.yaml with your configuration"
echo "2. Edit ${INSTALL_DIR}/.env with your secrets (passwords, API keys)"
echo "3. Enable the service: sudo systemctl enable cabinpi-daemon"
echo "4. Start the service: sudo systemctl start cabinpi-daemon"
echo "5. Check status: sudo systemctl status cabinpi-daemon"
echo "6. View logs: journalctl -u cabinpi-daemon -f"
echo
echo "To reload configuration: sudo systemctl reload cabinpi-daemon"
echo "To restart service: sudo systemctl restart cabinpi-daemon"
echo
