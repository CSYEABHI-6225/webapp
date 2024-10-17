#!/bin/bash
set -e

# Update package lists
sudo apt-get update

# Upgrade existing packages
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# Add universe repository
sudo add-apt-repository universe

# Update package lists again
sudo apt-get update

# Install dependencies
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-dev libmysqlclient-dev
# Install Python and pip
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-pip

# Install pkg-config (use pkgconf instead if pkg-config is not available)
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkg-config || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkgconf

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    build-essential

# Install gunicorn using pip
sudo pip3 install gunicorn

# Clean up
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
