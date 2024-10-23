#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh

    # Add current user to the docker group
    echo "Adding user to the Docker group..."
    sudo usermod -aG docker $USER

    # Verify Docker installation
    docker_version=$(docker --version)
    echo "Docker installed: $docker_version"
else
    echo "Docker is already installed: $(docker --version)"
fi

# Check if Docker Compose is installed
if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose plugin..."
    sudo apt-get install -y docker-compose-plugin

    # Verify Docker Compose installation
    compose_version=$(docker compose version)
    echo "Docker Compose installed: $compose_version"
else
    echo "Docker Compose is already installed: $(docker compose version)"
fi

sudo reboot