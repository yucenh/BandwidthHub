#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Optional EarnApp setup (native systemd service, not Docker)
if command -v earnapp &> /dev/null; then
    echo "EarnApp is already installed."
    earnapp status || true
else
    echo "If you don't have an EarnApp account, register here: https://earnapp.com/i/HwMhGQ7v"
    read -r -p "Install and configure EarnApp? [y/N] " install_earnapp
    if [[ "$install_earnapp" =~ ^[Yy]$ ]]; then
        wget -qO /tmp/earnapp.sh https://brightdata.com/static/earnapp/install.sh
        yes yes | sudo bash /tmp/earnapp.sh
        rm -f /tmp/earnapp.sh
        read -r -p "Open the link above to register your device, then press Enter to continue..."
    fi
fi

# Optional Mysterium Node setup (native systemd service, not Docker)
if command -v myst &> /dev/null; then
    echo "Mysterium Node is already installed ($(myst --version 2>/dev/null | awk '/Version:/ {print $2; exit}' || echo 'installed'))."
else
    echo "If you don't have a Mysterium Node account, register here: https://mystnodes.co/?referral_code=dHPdeDdN7KlghulnX395RCmWuWCCji13rk4z0Xzi"
    read -r -p "Install Mysterium Node (native dVPN exit node)? [y/N] " install_myst
    if [[ "$install_myst" =~ ^[Yy]$ ]]; then
        sudo -E bash -c "$(curl -fsSL https://raw.githubusercontent.com/mysteriumnetwork/node/master/install.sh)"
        LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        echo "Mysterium Node installed! Claim your node at: http://${LAN_IP:-localhost}:4449"
    fi
fi

# Load environment variables
if [[ -f ".env" ]]; then
    echo "Environment file found, proceeding..."
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
else
    echo "No .env file found. Copy .env.sample to .env and fill in your credentials first."
    exit 1
fi

if [[ -z "${DEVICE_ID:-}" ]]; then
    if command -v uuidgen &> /dev/null; then
        DEVICE_ID=$(uuidgen)
    elif [[ -r /proc/sys/kernel/random/uuid ]]; then
        DEVICE_ID=$(cat /proc/sys/kernel/random/uuid)
    elif command -v uuid &> /dev/null; then
        DEVICE_ID=$(uuid)
    else
        echo "No UUID generator found. Please set DEVICE_ID in .env or install uuid-runtime."
        exit 1
    fi
    export DEVICE_ID
fi
echo "DEVICE_ID is: $DEVICE_ID"

# Build the list of configured Docker services
services_to_start=()

if [[ -n "${RP_EMAIL:-}" && -n "${RP_API_KEY:-}" ]]; then
    services_to_start+=("repocket")
fi

if [[ -n "${HONEYGAIN_EMAIL:-}" && -n "${HONEYGAIN_PASSWORD:-}" ]]; then
    services_to_start+=("honeygain")
fi

if [[ -n "${PAWNSAPP_EMAIL:-}" && -n "${PAWNSAPP_PASSWORD:-}" ]]; then
    services_to_start+=("pawnsapp")
fi

if [[ -n "${PACKETSTREAM_CID:-}" ]]; then
    services_to_start+=("packetstream")
fi

if [[ ${#services_to_start[@]} -eq 0 ]]; then
    echo "No valid Docker service configurations found in .env."
    exit 0
fi

services_to_start+=("watchtower")
echo "Starting services: ${services_to_start[*]}"

DOCKER_CMD=(docker)
if ! docker info &> /dev/null; then
    DOCKER_CMD=(sudo -E docker)
fi

"${DOCKER_CMD[@]}" compose up -d --pull always --remove-orphans "${services_to_start[@]}"
