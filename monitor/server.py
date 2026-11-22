#!/usr/bin/env python3
"""Lightweight Raspberry Pi / Linux Passive-Income Traffic Monitor Web App.

Zero external dependencies (Python 3 standard library only).
Collects live stats from:
  - Host NIC (eth0 / default interface) & system metrics (/proc, /sys)
  - EarnApp systemd service (IPAccounting)
  - Mysterium Node local Tequilapi (127.0.0.1:4050)
  - BandwidthHub Docker containers via /var/run/docker.sock
Persists 5-minute traffic deltas in SQLite for hourly & daily trends.
"""

from __future__ import annotations

import concurrent.futures
import http.client
import json
import os
import re
import socket
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "history.db"
INDEX_PATH = BASE_DIR / "index.html"
PORT = int(os.environ.get("TRAFFIC_MONITOR_PORT", "8088"))
BIND_HOST = os.environ.get("TRAFFIC_MONITOR_HOST", "0.0.0.0")
DOCKER_SOCK = "/var/run/docker.sock"
SAMPLE_INTERVAL_SEC = 300  # 5 minutes
CACHE_TTL_SEC = 5


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 5.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        self.sock = sock


def docker_api(path: str, timeout: float = 5.0) -> bytes | None:
    try:
        conn = UnixHTTPConnection(DOCKER_SOCK, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        if resp.status == 200:
            return data
    except Exception:
        return None
    return None


def strip_docker_log_headers(raw: bytes) -> str:
    """Decode multiplexed Docker container log frames (or plain TTY logs)."""
    if not raw:
        return ""
    out: list[bytes] = []
    i = 0
    n = len(raw)
    multiplexed = n >= 8 and raw[0] in (0, 1, 2) and raw[1:4] == b"\x00\x00\x00"
    if not multiplexed:
        return raw.decode("utf-8", errors="replace")
    while i + 8 <= n:
        size = int.from_bytes(raw[i + 4 : i + 8], "big")
        i += 8
        if size < 0 or i + size > n:
            break
        out.append(raw[i : i + size])
        i += size
    return b"".join(out).decode("utf-8", errors="replace")


def get_host_stats() -> dict:
    uptime_sec = 0.0
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as f:
            uptime_sec = float(f.read().split()[0])
    except Exception:
        pass

    temp_c = None
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r", encoding="utf-8") as f:
            temp_c = round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass

    mem_total = mem_avail = 0
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    mem_avail = int(line.split()[1]) * 1024
    except Exception:
        pass

    disk_total = disk_used = 0
    try:
        st = os.statvfs("/")
        disk_total = st.f_blocks * st.f_frsize
        disk_used = (st.f_blocks - st.f_bfree) * st.f_frsize
    except Exception:
        pass

    load_avg = [0.0, 0.0, 0.0]
    try:
        load_avg = [round(x, 2) for x in os.getloadavg()]
    except Exception:
        pass

    iface = "eth0"
    if not os.path.isdir(f"/sys/class/net/{iface}"):
        try:
            r = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            parts = r.stdout.split()
            if "dev" in parts:
                iface = parts[parts.index("dev") + 1]
        except Exception:
            iface = ""

    nic_rx = nic_tx = 0
    if iface:
        try:
            with open(f"/sys/class/net/{iface}/statistics/rx_bytes") as f:
                nic_rx = int(f.read().strip())
            with open(f"/sys/class/net/{iface}/statistics/tx_bytes") as f:
                nic_tx = int(f.read().strip())
        except Exception:
            pass

    return {
        "hostname": socket.gethostname(),
        "uptime_sec": int(uptime_sec),
        "temp_c": temp_c,
        "load_avg": load_avg,
        "mem_total": mem_total,
        "mem_used": max(0, mem_total - mem_avail),
        "disk_total": disk_total,
        "disk_used": disk_used,
        "iface": iface,
        "nic_rx": nic_rx,
        "nic_tx": nic_tx,
    }


def get_earnapp_stats() -> dict:
    props = {}
    try:
        r = subprocess.run(
            [
                "systemctl",
                "show",
                "earnapp.service",
                "-p",
                "LoadState",
                "-p",
                "ActiveState",
                "-p",
                "SubState",
                "-p",
                "ActiveEnterTimestamp",
                "-p",
                "IPIngressBytes",
                "-p",
                "IPEgressBytes",
            ],
            capture_output=True,
            text=True,
            timeout=3,
        )
        for line in r.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                props[k] = v
    except Exception:
        pass

    def parse_int(val: str) -> int | None:
        return int(val) if val and val.isdigit() else None

    rx = parse_int(props.get("IPIngressBytes", ""))
    tx = parse_int(props.get("IPEgressBytes", ""))
    return {
        "name": "EarnApp",
        "key": "earnapp",
        "type": "systemd",
        "installed": props.get("LoadState") == "loaded",
        "status": props.get("ActiveState", "unknown"),
        "sub_state": props.get("SubState", ""),
        "since": props.get("ActiveEnterTimestamp", ""),
        "rx_bytes": rx or 0,
        "tx_bytes": tx or 0,
        "ip_accounting": rx is not None and tx is not None,
    }


def get_mysterium_stats() -> dict:
    state = "unknown"
    installed = False
    try:
        r = subprocess.run(
            ["systemctl", "show", "mysterium-node.service", "-p", "LoadState", "-p", "ActiveState"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        for line in r.stdout.splitlines():
            if line == "LoadState=loaded":
                installed = True
            elif line.startswith("ActiveState="):
                state = line.split("=", 1)[1]
    except Exception:
        pass

    def fetch(ep: str):
        with urllib.request.urlopen(f"http://127.0.0.1:4050/{ep}", timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))

    res: dict = {
        "name": "Mysterium Node",
        "key": "mysterium",
        "type": "systemd",
        "installed": installed,
        "status": state,
        "version": "",
        "uptime": "",
        "running_services": 0,
        "total_services": 0,
        "total_rx": 0,
        "total_tx": 0,
        "total_sessions": 0,
        "total_myst": 0.0,
        "daily": [],
        "today_rx": 0,
        "today_tx": 0,
        "today_myst": 0.0,
        "today_sessions": 0,
    }
    if not installed and state != "active":
        return res

    try:
        hc = fetch("healthcheck")
        res["version"] = hc.get("version", "")
        res["uptime"] = hc.get("uptime", "")

        svcs = fetch("services") or []
        res["total_services"] = len(svcs)
        res["running_services"] = sum(1 for s in svcs if s.get("status") == "Running")

        agg = fetch("sessions/stats-aggregated").get("stats", {})
        res["total_rx"] = int(agg.get("sum_bytes_received", 0))
        res["total_tx"] = int(agg.get("sum_bytes_sent", 0))
        res["total_sessions"] = int(agg.get("count", 0))
        res["total_myst"] = round(int(agg.get("sum_tokens", 0)) / 1e18, 4)

        daily_raw = fetch("sessions/stats-daily").get("items", {})
        daily_list = []
        today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for day, s in sorted(daily_raw.items())[-14:]:
            drx = int(s.get("sum_bytes_received", 0))
            dtx = int(s.get("sum_bytes_sent", 0))
            dmyst = round(int(s.get("sum_tokens", 0)) / 1e18, 4)
            dcnt = int(s.get("count", 0))
            entry = {
                "day": day,
                "rx_bytes": drx,
                "tx_bytes": dtx,
                "total_bytes": drx + dtx,
                "myst": dmyst,
                "sessions": dcnt,
            }
            daily_list.append(entry)
            if day == today_utc:
                res["today_rx"] = drx
                res["today_tx"] = dtx
                res["today_myst"] = dmyst
                res["today_sessions"] = dcnt
        res["daily"] = daily_list
    except Exception as e:
        res["error"] = str(e)

    return res


def _fetch_single_container_stats(c: dict) -> dict:
    cid = c["Id"]
    raw_name = (c.get("Names") or ["/unknown"])[0].lstrip("/")
    short_key = re.sub(r"^bandwidthhub[^-]*-|-1$", "", raw_name)
    nice_names = {
        "honeygain": "Honeygain",
        "pawnsapp": "PawnsApp",
        "repocket": "Repocket",
        "packetstream": "PacketStream",
        "watchtower": "Watchtower",
    }
    entry = {
        "id": cid[:12],
        "container": raw_name,
        "key": short_key,
        "name": nice_names.get(short_key, short_key),
        "image": c.get("Image", ""),
        "state": c.get("State", "unknown"),
        "status": c.get("Status", ""),
        "rx_bytes": 0,
        "tx_bytes": 0,
        "extra": {},
    }

    if c.get("State") == "running":
        s_raw = docker_api(f"/containers/{cid}/stats?stream=false&one-shot=true", timeout=4.0)
        if s_raw:
            try:
                st = json.loads(s_raw)
                nets = st.get("networks") or {}
                entry["rx_bytes"] = sum(int(v.get("rx_bytes", 0)) for v in nets.values())
                entry["tx_bytes"] = sum(int(v.get("tx_bytes", 0)) for v in nets.values())
            except Exception:
                pass

        if short_key == "pawnsapp":
            l_raw = docker_api(f"/containers/{cid}/logs?stdout=1&stderr=1&tail=40", timeout=3.0)
            if l_raw:
                text = strip_docker_log_headers(l_raw)
                for line in reversed(text.splitlines()):
                    if "balance_ready" in line:
                        try:
                            d = json.loads(line.strip())
                            p = d.get("parameters", {})
                            entry["extra"] = {
                                "balance": p.get("balance", ""),
                                "reported_traffic": p.get("traffic", ""),
                                "reported_at": d.get("happened_at", ""),
                            }
                            break
                        except Exception:
                            pass
    return entry


def get_docker_containers() -> list[dict]:
    raw = docker_api("/containers/json?all=1", timeout=4.0)
    if not raw:
        return []
    try:
        all_c = json.loads(raw)
    except Exception:
        return []

    bh = [
        c
        for c in all_c
        if any(n.lstrip("/").startswith("bandwidthhub") for n in (c.get("Names") or []))
    ]
    if not bh:
        return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(bh))) as ex:
        results = list(ex.map(_fetch_single_container_stats, bh))

    order = {"honeygain": 1, "repocket": 2, "pawnsapp": 3, "packetstream": 4, "watchtower": 99}
    results.sort(key=lambda x: (order.get(x["key"], 50), x["name"]))
    return results


# ---------------- SQLite History Tracker ----------------

DB_LOCK = threading.Lock()


def init_db() -> None:
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS last_counters (
                service TEXT PRIMARY KEY,
                rx_bytes INTEGER NOT NULL,
                tx_bytes INTEGER NOT NULL,
                updated_ts INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traffic_deltas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                day TEXT NOT NULL,
                hour TEXT NOT NULL,
                service TEXT NOT NULL,
                rx_delta INTEGER NOT NULL,
                tx_delta INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deltas_ts ON traffic_deltas(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_deltas_day ON traffic_deltas(day, service)")
        conn.commit()
        conn.close()


def record_snapshot(overview: dict) -> None:
    now_dt = datetime.now()
    now_ts = int(now_dt.timestamp())
    day_str = now_dt.strftime("%Y-%m-%d")
    hour_str = now_dt.strftime("%Y-%m-%d %H:00")

    counters: dict[str, tuple[int, int]] = {}
    host = overview.get("host", {})
    counters["host_nic"] = (int(host.get("nic_rx", 0)), int(host.get("nic_tx", 0)))

    ea = overview.get("earnapp", {})
    if ea.get("ip_accounting"):
        counters["earnapp"] = (int(ea.get("rx_bytes", 0)), int(ea.get("tx_bytes", 0)))

    myst = overview.get("mysterium", {})
    if myst.get("total_rx", 0) or myst.get("total_tx", 0):
        counters["mysterium"] = (int(myst.get("total_rx", 0)), int(myst.get("total_tx", 0)))

    for c in overview.get("containers", []):
        if c.get("key") != "watchtower":
            counters[c["key"]] = (int(c.get("rx_bytes", 0)), int(c.get("tx_bytes", 0)))

    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        for svc, (rx, tx) in counters.items():
            row = cur.execute(
                "SELECT rx_bytes, tx_bytes FROM last_counters WHERE service = ?", (svc,)
            ).fetchone()
            if row is not None:
                prev_rx, prev_tx = row
                drx = rx - prev_rx if rx >= prev_rx else rx
                dtx = tx - prev_tx if tx >= prev_tx else tx
                if drx > 0 or dtx > 0:
                    cur.execute(
                        "INSERT INTO traffic_deltas (ts, day, hour, service, rx_delta, tx_delta) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (now_ts, day_str, hour_str, svc, drx, dtx),
                    )
            cur.execute(
                "INSERT INTO last_counters (service, rx_bytes, tx_bytes, updated_ts) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(service) DO UPDATE SET "
                "rx_bytes=excluded.rx_bytes, tx_bytes=excluded.tx_bytes, updated_ts=excluded.updated_ts",
                (svc, rx, tx, now_ts),
            )

        cutoff = now_ts - 35 * 86400
        cur.execute("DELETE FROM traffic_deltas WHERE ts < ?", (cutoff,))
        conn.commit()
        conn.close()


def get_today_totals() -> dict[str, dict]:
    today_str = datetime.now().strftime("%Y-%m-%d")
    out: dict[str, dict] = {}
    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        rows = conn.execute(
            "SELECT service, SUM(rx_delta), SUM(tx_delta) FROM traffic_deltas "
            "WHERE day = ? GROUP BY service",
            (today_str,),
        ).fetchall()
        conn.close()
    for svc, rx, tx in rows:
        out[svc] = {"rx_bytes": int(rx or 0), "tx_bytes": int(tx or 0)}
    return out


def get_history(hours: int = 24) -> dict:
    hours = max(1, min(hours, 168))
    now_dt = datetime.now()
    since_ts = int((now_dt - timedelta(hours=hours)).timestamp())

    with DB_LOCK:
        conn = sqlite3.connect(DB_PATH)
        hourly_rows = conn.execute(
            "SELECT hour, service, SUM(rx_delta), SUM(tx_delta) "
            "FROM traffic_deltas WHERE ts >= ? GROUP BY hour, service ORDER BY hour ASC",
            (since_ts,),
        ).fetchall()
        daily_rows = conn.execute(
            "SELECT day, service, SUM(rx_delta), SUM(tx_delta) "
            "FROM traffic_deltas GROUP BY day, service ORDER BY day ASC"
        ).fetchall()
        first_ts_row = conn.execute("SELECT MIN(updated_ts) FROM last_counters").fetchone()
        conn.close()

    hourly_map: dict[str, dict[str, dict]] = {}
    for h, svc, rx, tx in hourly_rows:
        hourly_map.setdefault(h, {})[svc] = {"rx": int(rx or 0), "tx": int(tx or 0)}

    hourly = []
    start_hour = now_dt.replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours - 1)
    for i in range(hours):
        h_key = (start_hour + timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
        hourly.append({"hour": h_key, "services": hourly_map.get(h_key, {})})

    daily_map: dict[str, dict[str, dict]] = {}
    for d, svc, rx, tx in daily_rows:
        daily_map.setdefault(d, {})[svc] = {"rx": int(rx or 0), "tx": int(tx or 0)}
    daily = [{"day": d, "services": daily_map[d]} for d in sorted(daily_map.keys())[-14:]]

    return {
        "tracking_since": first_ts_row[0] if first_ts_row and first_ts_row[0] else None,
        "hourly": hourly,
        "daily": daily,
    }


# ---------------- Cache & Background Sampler ----------------

CACHE_LOCK = threading.Lock()
CACHE_DATA: dict | None = None
CACHE_TIME: float = 0.0


def collect_overview(force: bool = False) -> dict:
    global CACHE_DATA, CACHE_TIME
    now = time.time()
    with CACHE_LOCK:
        if not force and CACHE_DATA is not None and (now - CACHE_TIME) < CACHE_TTL_SEC:
            return CACHE_DATA

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        f_host = ex.submit(get_host_stats)
        f_ea = ex.submit(get_earnapp_stats)
        f_myst = ex.submit(get_mysterium_stats)
        f_docker = ex.submit(get_docker_containers)

        host = f_host.result()
        earnapp = f_ea.result()
        mysterium = f_myst.result()
        containers = f_docker.result()

    today_tracked = get_today_totals()
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z").strip(),
        "epoch": int(time.time()),
        "host": host,
        "earnapp": earnapp,
        "mysterium": mysterium,
        "containers": containers,
        "today_tracked": today_tracked,
    }
    with CACHE_LOCK:
        CACHE_DATA = data
        CACHE_TIME = time.time()
    return data


def sampler_loop() -> None:
    while True:
        try:
            ov = collect_overview(force=True)
            record_snapshot(ov)
        except Exception:
            pass
        time.sleep(SAMPLE_INTERVAL_SEC)


# ---------------- HTTP Handler ----------------


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path in ("/", "/index.html"):
            try:
                html = INDEX_PATH.read_bytes()
                self._send(200, html, "text/html; charset=utf-8")
            except Exception as e:
                self._send(500, f"Error loading UI: {e}".encode(), "text/plain")
            return

        if parsed.path == "/api/overview":
            force = qs.get("refresh", ["0"])[0] == "1"
            ov = collect_overview(force=force)
            if force:
                record_snapshot(ov)
                ov["today_tracked"] = get_today_totals()
            self._send(200, json.dumps(ov).encode("utf-8"), "application/json")
            return

        if parsed.path == "/api/history":
            try:
                hours = int(qs.get("hours", ["24"])[0])
            except ValueError:
                hours = 24
            hist = get_history(hours=hours)
            self._send(200, json.dumps(hist).encode("utf-8"), "application/json")
            return

        self._send(404, b'{"error":"not found"}', "application/json")


def main() -> None:
    init_db()
    t = threading.Thread(target=sampler_loop, daemon=True)
    t.start()

    server = ThreadingHTTPServer((BIND_HOST, PORT), Handler)
    print(f"BandwidthHub Monitor listening on http://{BIND_HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
