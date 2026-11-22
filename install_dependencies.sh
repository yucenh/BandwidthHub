#!/usr/bin/env bash
set -euo pipefail

NEEDS_REBOOT=false

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
    sudo sh /tmp/get-docker.sh
    rm -f /tmp/get-docker.sh

    TARGET_USER="${SUDO_USER:-$USER}"
    echo "Adding $TARGET_USER to the docker group..."
    sudo usermod -aG docker "$TARGET_USER"

    echo "Docker installed: $(docker --version)"
    NEEDS_REBOOT=true
else
    echo "Docker is already installed: $(docker --version)"
fi

# Check if Docker Compose plugin is installed
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    echo "Docker Compose installed: $(docker compose version)"
else
    echo "Docker Compose is already installed: $(docker compose version)"
fi

if [[ "$NEEDS_REBOOT" == "true" ]]; then
    echo "Docker was just installed and group membership was updated."
    read -r -p "Reboot now to apply group changes? [y/N] " do_reboot
    if [[ "$do_reboot" =~ ^[Yy]$ ]]; then
        sudo reboot
    else
        echo "Please log out and back in (or reboot) before running start_earning.sh."
    fi
fi
