#!/bin/bash

echo "If you don't have an EarnApp account, register here: https://earnapp.com/i/HwMhGQ7v"

# Wait for the user to press Enter to continue
read -p "Press Enter to continue with the EarnApp setup..."

wget -qO- https://brightdata.com/static/earnapp/install.sh > /tmp/earnapp.sh && yes yes | sudo bash /tmp/earnapp.sh

read -p "Login above link and press Enter to continue..."

# Check if the required environment files or configs exist
if [[ -f ".env" ]]; then
    echo "Environment file found, proceeding..."
    set -a
    source .env
    set +a
else
    echo "No environment file found, exiting."
    exit 1
fi

if [ -z "$DEVICE_ID" ]; then
    if command -v uuidgen &> /dev/null; then
        DEVICE_ID=$(uuidgen) 
    elif command -v uuid &> /dev/null; then
        DEVICE_ID=$(uuid)
    else
        echo "No UUID generator found. Please install uuidgen or uuid."
        exit 1
    fi
    export DEVICE_ID
fi
echo "DEVICE_ID is: $DEVICE_ID"

# Define an array of services and their corresponding config files (if required)
services_to_start=()

# Check each service's configuration and decide whether to bring it up
if [[ -n "$RP_EMAIL" && -n "$RP_API_KEY" ]]; then
    services_to_start+=("repocket")
fi

if [[ -n "$HONEYGAIN_EMAIL" && -n "$HONEYGAIN_PASSWORD" ]]; then
    services_to_start+=("honeygain")
fi

if [[ -n "$TRAFFICMONETIZER_TOKEN" ]]; then
    services_to_start+=("trafficmonetizer")
    TRAFFIC_MONETIZER_IMAGE="traffmonetizer/cli_v2:latest"
    if [ "$(uname -m)" = "aarch64" ]; then
        TRAFFIC_MONETIZER_IMAGE="traffmonetizer/cli_v2:arm64v8"
    elif [ "$(uname -m)" = "armv7l" ]; then
        TRAFFIC_MONETIZER_IMAGE="traffmonetizer/cli_v2:arm32v7"
    fi
    export TRAFFIC_MONETIZER_IMAGE
fi

if [[ -n "$PAWNSAPP_EMAIL" && -n "$PAWNSAPP_PASSWORD" ]]; then
    services_to_start+=("pawnsapp")
fi

if [[ -n "$PACKETSTREAM_CID" ]]; then
    services_to_start+=("packetstream")
fi

# Start services if any are valid
if [ ${#services_to_start[@]} -gt 0 ]; then
    services_to_start+=("watchtower")
    echo "Starting services: ${services_to_start[*]}"
    sudo -E docker compose up -d ${services_to_start[@]}
else
    echo "No valid configurations found for any services."
fi
