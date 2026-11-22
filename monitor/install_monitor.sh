#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"
TARGET_GROUP="$(id -gn "$TARGET_USER")"
PORT="${TRAFFIC_MONITOR_PORT:-8088}"

# Enable systemd IPAccounting for EarnApp if installed and not already enabled
if systemctl list-unit-files earnapp.service &>/dev/null && [[ "$(systemctl show -p LoadState --value earnapp.service 2>/dev/null)" == "loaded" ]]; then
    if [[ "$(systemctl show -p IPAccounting --value earnapp.service 2>/dev/null)" != "yes" ]]; then
        echo "Enabling systemd IPAccounting for earnapp.service..."
        sudo mkdir -p /etc/systemd/system/earnapp.service.d
        printf '[Service]\nIPAccounting=yes\n' | sudo tee /etc/systemd/system/earnapp.service.d/ip-accounting.conf >/dev/null
        sudo systemctl daemon-reload
        sudo systemctl restart earnapp.service || true
    else
        echo "EarnApp IPAccounting is already enabled."
    fi
fi

# Build supplementary groups (docker, and video if present for Raspberry Pi temp)
SUPP_GROUPS=()
getent group docker &>/dev/null && SUPP_GROUPS+=("docker")
getent group video &>/dev/null && SUPP_GROUPS+=("video")
SUPP_LINE=""
if [[ ${#SUPP_GROUPS[@]} -gt 0 ]]; then
    SUPP_LINE="SupplementaryGroups=${SUPP_GROUPS[*]}"
fi

chmod +x "$SCRIPT_DIR/server.py" "$SCRIPT_DIR/traffic_report.sh"

echo "Installing systemd service: traffic-monitor.service (port $PORT)..."
sudo tee /etc/systemd/system/traffic-monitor.service >/dev/null <<EOF
[Unit]
Description=BandwidthHub Lightweight Traffic Monitor
After=network-online.target docker.service earnapp.service mysterium-node.service
Wants=network-online.target

[Service]
Type=simple
User=${TARGET_USER}
Group=${TARGET_GROUP}
${SUPP_LINE}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 ${SCRIPT_DIR}/server.py
Environment=TRAFFIC_MONITOR_PORT=${PORT}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now traffic-monitor.service

LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
echo "Traffic monitor is running!"
echo "Open in your browser: http://${LAN_IP:-localhost}:${PORT}"
