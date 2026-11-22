#!/usr/bin/env bash
set -uo pipefail

human_bytes() {
    python3 -c '
import sys
b = float(sys.argv[1])
for unit in ["B", "KB", "MB", "GB", "TB"]:
    if b < 1024 or unit == "TB":
        print(f"{b:.2f} {unit}" if unit != "B" else f"{int(b)} B")
        break
    b /= 1024.0
' "$1" 2>/dev/null || echo "$1 B"
}

DOCKER_CMD=(docker)
if ! docker info &>/dev/null; then
    DOCKER_CMD=(sudo docker)
fi

echo "============================================================"
echo "  BandwidthHub Traffic Report"
echo "  Time: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "============================================================"

UPTIME_STR=$(uptime -p 2>/dev/null || uptime)
TEMP_STR=$(vcgencmd measure_temp 2>/dev/null | cut -d= -f2 || echo "N/A")
IFACE="eth0"
[[ -d "/sys/class/net/$IFACE" ]] || IFACE=$(ip route show default 2>/dev/null | awk '/default/ {print $5; exit}')

echo "Host   : $UPTIME_STR | Temp: $TEMP_STR"
if [[ -n "${IFACE:-}" && -r "/sys/class/net/$IFACE/statistics/rx_bytes" ]]; then
    NIC_RX=$(cat "/sys/class/net/$IFACE/statistics/rx_bytes")
    NIC_TX=$(cat "/sys/class/net/$IFACE/statistics/tx_bytes")
    echo "NIC    : $IFACE -> RX $(human_bytes "$NIC_RX") / TX $(human_bytes "$NIC_TX") (since boot)"
fi
echo ""

# 1. EarnApp
if [[ "$(systemctl show -p LoadState --value earnapp.service 2>/dev/null)" == "loaded" ]]; then
    echo "--- [1] EarnApp (systemd, since service start) ---"
    EA_STATE=$(systemctl is-active earnapp.service 2>/dev/null || echo "unknown")
    EA_SINCE=$(systemctl show earnapp.service -p ActiveEnterTimestamp --value 2>/dev/null || echo "N/A")
    EA_RX=$(systemctl show earnapp.service -p IPIngressBytes --value 2>/dev/null || echo "")
    EA_TX=$(systemctl show earnapp.service -p IPEgressBytes --value 2>/dev/null || echo "")
    if [[ "$EA_RX" =~ ^[0-9]+$ && "$EA_TX" =~ ^[0-9]+$ ]]; then
        echo "Status : $EA_STATE (since $EA_SINCE)"
        echo "Traffic: RX $(human_bytes "$EA_RX") / TX $(human_bytes "$EA_TX")"
    else
        echo "Status : $EA_STATE (IPAccounting not enabled; run monitor/install_monitor.sh)"
    fi
    echo ""
fi

# 2. Mysterium Node (optional)
if [[ "$(systemctl show -p LoadState --value mysterium-node.service 2>/dev/null)" == "loaded" ]]; then
    echo "--- [2] Mysterium Node (Tequilapi) ---"
    MYST_STATE=$(systemctl is-active mysterium-node.service 2>/dev/null || echo "unknown")
    MYST_VER=$(curl -s --max-time 3 http://127.0.0.1:4050/healthcheck 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("version","?"))' 2>/dev/null || echo "N/A")
    echo "Status : $MYST_STATE (v$MYST_VER)"
    python3 - <<'PY'
import urllib.request, json

def fetch(path):
    with urllib.request.urlopen(f"http://127.0.0.1:4050/{path}", timeout=3) as r:
        return json.loads(r.read())

try:
    agg = fetch("sessions/stats-aggregated").get("stats", {})
    rx = agg.get("sum_bytes_received", 0) / 1e9
    tx = agg.get("sum_bytes_sent", 0) / 1e9
    tot_tb = (rx + tx) / 1000.0
    myst = agg.get("sum_tokens", 0) / 1e18
    cnt = agg.get("count", 0)
    print(f"Total  : {tot_tb:.2f} TB (RX {rx/1000:.2f} TB / TX {tx:.1f} GB) | {cnt} sessions | {myst:.2f} MYST")

    daily = fetch("sessions/stats-daily").get("items", {})
    days = sorted(daily.items())[-7:]
    if days:
        print("Last 7d:")
        for day, s in days:
            drx = s.get("sum_bytes_received", 0) / 1e9
            dtx = s.get("sum_bytes_sent", 0) / 1e9
            dmyst = s.get("sum_tokens", 0) / 1e18
            dcnt = s.get("count", 0)
            print(f"  {day}  total={drx+dtx:6.2f} GB (RX {drx:5.2f} / TX {dtx:4.2f}) | {dcnt:3d} sess | {dmyst:.4f} MYST")
except Exception as e:
    print(f"Tequilapi unavailable: {e}")
PY
    echo ""
fi

# 3. BandwidthHub Docker Containers
echo "--- [3] BandwidthHub Docker Containers (since container start) ---"
mapfile -t CONTAINERS < <("${DOCKER_CMD[@]}" ps --filter "name=bandwidthhub" --format "{{.Names}}" 2>/dev/null | sort)
if [[ ${#CONTAINERS[@]} -gt 0 ]]; then
    declare -A STATUS_MAP
    while IFS=$'\t' read -r cname cstatus; do
        STATUS_MAP["$cname"]="$cstatus"
    done < <("${DOCKER_CMD[@]}" ps --filter "name=bandwidthhub" --format "{{.Names}}\t{{.Status}}" 2>/dev/null)

    printf "%-30s %-24s %-22s %s\n" "CONTAINER" "STATUS" "NET I/O (RX / TX)" "CPU"
    while IFS=$'\t' read -r cname netio cpu; do
        printf "%-30s %-24s %-22s %s\n" "$cname" "${STATUS_MAP[$cname]:-unknown}" "$netio" "$cpu"
    done < <("${DOCKER_CMD[@]}" stats --no-stream --format "{{.Name}}\t{{.NetIO}}\t{{.CPUPerc}}" "${CONTAINERS[@]}" 2>/dev/null | sort)

    if printf '%s\n' "${CONTAINERS[@]}" | grep -qx "bandwidthhub-pawnsapp-1"; then
        PAWNS_LINE=$("${DOCKER_CMD[@]}" logs --tail 50 bandwidthhub-pawnsapp-1 2>&1 | grep "balance_ready" | tail -n 1 || true)
        if [[ -n "$PAWNS_LINE" ]]; then
            python3 -c '
import sys, json
d = json.loads(sys.argv[1])
p = d.get("parameters", {})
bal = p.get("balance", "?")
traf = p.get("traffic", "?")
ts = d.get("happened_at", "?")
print(f"\nPawnsApp reported: balance={bal}, traffic={traf} (at {ts})")
' "$PAWNS_LINE" 2>/dev/null || true
        fi
    fi
else
    echo "No running bandwidthhub containers found."
fi
echo "============================================================"
