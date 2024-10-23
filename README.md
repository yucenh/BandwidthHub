# BandwidthHub

**BandwidthHub** is a comprehensive tool that consolidates multiple traffic-sharing services, enabling you to earn passive income effortlessly by sharing your unused internet bandwidth. With BandwidthHub, you can wrap and manage services like Repocket, Bitping, Honeygain, TrafficMonetizer, PawnsApp, and PacketStream all in one place, maximizing your earnings from every megabyte. It operates seamlessly in the background and keeps everything up to date automatically using Watchtower, allowing you to sit back and watch your earnings grow. It’s OK for older computers, as it requires minimal resources to run.

## Keywords

- **Passive Income**: Monetize your idle internet bandwidth with ease across multiple platforms.
- **Home Sparse Bandwidth Monetization**: Ideal for home networks, BandwidthHub optimizes your internet usage to help you earn more.
- **Raspberry Pi**: Fully functional on Raspberry Pi devices, making it perfect for DIY tech enthusiasts.
- **Centralized Management**: Manage all your traffic-sharing services from a single, easy-to-use interface.
- **Easy Setup**: Register on the supported platforms, configure environment variables, and start earning right away.
- **Supported Platforms**: Integrates seamlessly with services like Repocket, Bitping, Honeygain, TrafficMonetizer, PawnsApp, and PacketStream.


## Supported Services

If you don't yet have an account for these platforms, you can register using the referral links below to support the development and maintenance of BandwidthHub. If you prefer not to use referral links, you can visit the official websites directly.

- **Honeygain** – [Register here using referral link](https://r.honeygain.me/YUCEN59984) | [No referral link](https://honeygain.com)
- **EarnApp** – [Register here using referral link](https://earnapp.com/i/HwMhGQ7v) | [No referral link](https://earnapp.com)
- **Repocket** – [Register here using referral link](https://link.repocket.com/6puI) | [No referral link](https://repocket.com/)
- **Bitping** –  [No referral link](https://bitping.com)
- **TrafficMonetizer** – [Register here using referral link](https://traffmonetizer.com/?aff=1781613) | [No referral link](https://traffmonetizer.com)
- **PawnsApp** – [Register here using referral link](https://pawns.app/?r=7782721) | [No referral link](https://pawns.app)
- **PacketStream** – [Register here using referral link](https://packetstream.io/?psr=6lY3) | [No referral link](https://packetstream.io)

By registering through these referral links, you can support BandwidthHub’s development while earning passive income through your shared internet bandwidth. However, if you prefer, you can use the non-referral links to register directly on the official websites.

## Prerequisites

- A Debian-based operating system (e.g., Ubuntu, Debian, Raspberry Pi OS) with a stable network connection. This project has been successfully tested on a Raspberry Pi 4.

## Getting Started

1. Download this repository: Run the following commands in your terminal:

    ```bash
    wget https://github.com/yucenh/BandwidthHub/archive/refs/heads/main.zip
    unzip main.zip
    cd BandwidthHub-main/
2. Create and Configure the `.env` File
    ```bash
    cp .env.sample .env
    nano .env
3. **Update system packages, install dependencies, and start services**: Ensure that Docker and Docker Compose are installed on your system. Execute the following commands:
    > **Note:** The `install_dependencies.sh` script will trigger a reboot. The following commands take several minutes to complete.
    ```bash
    sudo apt update
    sudo ./install_dependencies.sh
    sudo ./start_earning.sh
4.  **Track Your Earnings**: Earnings may take some time to appear in the dashboards of different platforms. You should be able to see your earnings within a few hours.

## Contributing
Contributions are welcome! Feel free to submit a pull request or open an issue for any bugs, feature requests, or improvements. Let’s make BandwidthHub the best tool for passive income.

## Disclaimer
BandwidthHub aggregates several third-party services. Please read and follow the terms and conditions of each platform to avoid any legal or usage issues.

## License
This project is licensed under the MIT License.


![visitors](https://visitor-badge.laobi.icu/badge?page_id=yucenh.BandwidthHub)
