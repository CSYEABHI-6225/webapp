#!/bin/bash
set -e

# Create the directory with correct permissions
sudo mkdir -p /opt/csye6225/webapp
sudo chown -R ubuntu:ubuntu /opt/csye6225/webapp

# Create a virtual environment
python3 -m venv /opt/csye6225/webapp/venv

# Activate the virtual environment
source /opt/csye6225/webapp/venv/bin/activate

source /tmp/webapp/.env

# Install required packages
pip install Flask SQLAlchemy mysqlclient pytest pytest-flask pymysql python-dotenv Flask-SQLAlchemy flask-httpauth cryptography boto3 watchtower statsd Flask-Migrate

# Ensure all files are copied to the correct location
cp -r /tmp/webapp/* /opt/csye6225/webapp/

# Set correct permissions
sudo chown -R ubuntu:ubuntu /opt/csye6225/webapp

# Deactivate the virtual environment
deactivate