#!/bin/bash
set -e

# Create csye6225 user and group
sudo groupadd csye6225
sudo useradd -m -s /bin/bash -g csye6225 csye6225

# Set up application directory
sudo mkdir -p /opt/csye6225/webapp
sudo chown -R csye6225:csye6225 /opt/csye6225

# Copy application files
sudo cp -R /tmp/webapp/* /opt/csye6225/webapp/
sudo cp -R /tmp/webapp/.env /opt/csye6225/webapp/

cd /opt/csye6225/webapp/ && ls -al

# Set correct permissions
sudo chown -R csye6225:csye6225 /opt/csye6225/webapp

# Create a requirements.txt file if it doesn't exist
if [ ! -f "/opt/csye6225/webapp/requirements.txt" ]; then
    sudo -u csye6225 bash -c 'echo "Flask==2.0.1" > /opt/csye6225/webapp/requirements.txt'
    sudo -u csye6225 bash -c 'echo "SQLAlchemy==1.4.23" >> /opt/csye6225/webapp/requirements.txt'
    sudo -u csye6225 bash -c 'echo "mysqlclient==2.0.3" >> /opt/csye6225/webapp/requirements.txt'
    # Add other required packages
fi



sudo chown ubuntu:ubuntu /opt/csye6225/webapp/.env
sudo chmod 600 /opt/csye6225/webapp/.env

# Set up virtual environment for the application
sudo -u csye6225 python3 -m venv /opt/csye6225/webapp/venv
sudo -u csye6225 /opt/csye6225/webapp/venv/bin/pip install -r /opt/csye6225/webapp/requirements.txt

echo "User creation and application setup completed."