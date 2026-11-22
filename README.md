# BandwidthHub

**BandwidthHub** is a lightweight Docker Compose setup that consolidates multiple bandwidth-sharing services so you can earn passive income from unused internet bandwidth. It supports Repocket, Honeygain, PawnsApp, PacketStream, EarnApp, and Mysterium Node, keeps BandwidthHub containers up to date automatically using Watchtower (`nickfedor/watchtower`), and includes a lightweight local web traffic monitor. It runs smoothly on both `amd64` and `arm64` devices, including Raspberry Pi.

## Features

- **Passive Income**: Monetize idle home bandwidth across multiple platforms from a single configuration.
- **ARM64 & x86_64 Ready**: All included Docker images natively support `linux/amd64` and `linux/arm64` (tested on Raspberry Pi).
- **Scoped Auto-Updates**: Uses `nickfedor/watchtower` with label filtering (`--label-enable`) to update only BandwidthHub containers once a day, leaving other containers untouched.
- **SD-Card Friendly Logging**: Caps Docker JSON log files (`10m` × 3) to prevent unbounded disk growth.
- **Simple Setup**: Fill in `.env` for the services you want to use and run `./start_earning.sh`.

## Supported Services

If you don't yet have an account on these platforms, you can register using the referral links below to support BandwidthHub, or use the direct links instead.

- **Honeygain** – [Referral link](https://r.honeygain.me/YUCEN59984) | [Direct link](https://honeygain.com)
- **EarnApp** – [Referral link](https://earnapp.com/i/HwMhGQ7v) | [Direct link](https://earnapp.com)
- **Mysterium Node** *(optional native dVPN node)* – [Referral link](https://mystnodes.co/?referral_code=dHPdeDdN7KlghulnX395RCmWuWCCji13rk4z0Xzi) | [Direct link](https://mystnodes.com)
- **Repocket** – [Referral link](https://link.repocket.com/6puI) | [Direct link](https://repocket.com/)
- **PawnsApp** – [Referral link](https://pawns.app/?r=7782721) | [Direct link](https://pawns.app)
- **PacketStream** – [Referral link](https://packetstream.io/?psr=6lY3) | [Direct link](https://packetstream.io)

## Realistic Earnings Estimate

- **US residential IP (24/7 on a Raspberry Pi 4)**: roughly **~$150–200 / year per IP** combined across the stack (typically led by EarnApp and Mysterium Node, with Honeygain, PawnsApp, Repocket, and PacketStream adding incremental earnings), while a Raspberry Pi 4 draws only ~4–5W of power.
- **Note**: Actual earnings vary significantly by country/region, demand, uptime, and IP type. Residential home IPs earn the most; datacenter/VPS IPs are usually blocked or earn close to zero. Running multiple devices on the same IP does not multiply earnings, and an **unlimited** internet plan is strongly recommended.

## Prerequisites

- A Linux system (e.g., Debian, Ubuntu, Raspberry Pi OS) with a stable residential internet connection.
- `git`, Docker, and the Docker Compose plugin.

## Getting Started

1. **Clone this repository**:

    ```bash
    git clone https://github.com/yucenh/BandwidthHub.git
    cd BandwidthHub
    ```

2. **Create and configure `.env`** (leave any unused service blank):

    ```bash
    cp .env.sample .env
    nano .env
    ```

3. **Install dependencies (if Docker / Docker Compose is not installed yet)**:

    ```bash
    chmod +x install_dependencies.sh start_earning.sh
    ./install_dependencies.sh
    ```

4. **Start earning**:

    ```bash
    ./start_earning.sh
    ```

5. **Track your earnings**: Earnings usually appear in each platform's dashboard within a few hours.

## Updating & Managing Services

- **Pull repo updates and latest container images**:

    ```bash
    git pull
    ./start_earning.sh
    ```

- **Check container status / logs**:

    ```bash
    docker compose ps
    docker compose logs --tail=50
    ```

- **Stop and remove all BandwidthHub containers**:

    ```bash
    docker compose down
    ```

## Optional: Lightweight Traffic Monitor

BandwidthHub includes an optional, zero-dependency Python 3 web dashboard (`monitor/`) and CLI report script (~23 MB RAM) to track per-service traffic, system health, and 24-hour trends in SQLite (with an **EN / 中文** toggle in the UI).

- **Install and start the web dashboard** (runs on port `8088` as a systemd service, and automatically enables kernel `IPAccounting` for EarnApp):

    ```bash
    chmod +x monitor/install_monitor.sh
    ./monitor/install_monitor.sh
    ```

  Then open `http://<your-device-ip>:8088` in your browser.

- **Quick CLI traffic summary**:

    ```bash
    ./monitor/traffic_report.sh
    ```

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue for bugs, feature requests, or improvements.

## Disclaimer

BandwidthHub aggregates third-party services. Please read and follow each platform's terms of service before running them.

## License

This project is licensed under the MIT License.

![visitors](https://visitor-badge.laobi.icu/badge?page_id=yucenh.BandwidthHub)
