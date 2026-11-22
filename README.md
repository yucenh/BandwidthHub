# BandwidthHub

**BandwidthHub** is a lightweight Docker Compose setup that consolidates multiple bandwidth-sharing services so you can earn passive income from unused internet bandwidth. It supports Repocket, Honeygain, PawnsApp, PacketStream, and EarnApp, and keeps BandwidthHub containers up to date automatically using Watchtower (`nickfedor/watchtower`). It runs smoothly on both `amd64` and `arm64` devices, including Raspberry Pi.

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
- **Repocket** – [Referral link](https://link.repocket.com/6puI) | [Direct link](https://repocket.com/)
- **PawnsApp** – [Referral link](https://pawns.app/?r=7782721) | [Direct link](https://pawns.app)
- **PacketStream** – [Referral link](https://packetstream.io/?psr=6lY3) | [Direct link](https://packetstream.io)

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

## Contributing

Contributions are welcome! Feel free to submit a pull request or open an issue for bugs, feature requests, or improvements.

## Disclaimer

BandwidthHub aggregates third-party services. Please read and follow each platform's terms of service before running them.

## License

This project is licensed under the MIT License.

![visitors](https://visitor-badge.laobi.icu/badge?page_id=yucenh.BandwidthHub)
