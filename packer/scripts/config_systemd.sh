#!/bin/bash
set -e

# Create systemd service file
cat << EOF | sudo tee /etc/systemd/system/webapp.service
[Unit]
Description=CSYE6225 WebApp
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/csye6225/webapp
Environment="PATH=/opt/csye6225/webapp/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/csye6225/webapp/.env
ExecStart=/bin/bash -c 'source /opt/csye6225/webapp/venv/bin/activate && python3 webapp.py'
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd, enable and start the service
sudo systemctl daemon-reload
sudo systemctl enable webapp.service
sudo systemctl start webapp.service