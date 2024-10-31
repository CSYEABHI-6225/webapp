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

# Install pkg-config
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkg-config || sudo DEBIAN_FRONTEND=noninteractive apt-get install -y pkgconf

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    build-essential

# Install CloudWatch agent
wget https://s3.amazonaws.com/amazoncloudwatch-agent/ubuntu/amd64/latest/amazon-cloudwatch-agent.deb
sudo dpkg -i -E ./amazon-cloudwatch-agent.deb

# Create CloudWatch agent configuration
echo "Creating temporary CloudWatch configuration file at /tmp/cloudwatch-config.json..."
cat > /tmp/cloudwatch-config.json <<'CLOUDWATCH_EOF'
{
  "agent": {
      "metrics_collection_interval": 10,
      "logfile": "/var/log/amazon-cloudwatch-agent.log"
  },
  "logs": {
      "logs_collected": {
          "files": {
              "collect_list": [
                  {
                      "file_path": "/opt/csye6225/webapp/log/webapp.log",
                      "log_group_name": "csye6225",
                      "log_stream_name": "webapp"
                  }
              ]
          }
      }
  },
  "metrics": {
    "metrics_collected": {
       "statsd": {
          "service_address": ":8125",
          "metrics_collection_interval": 15,
          "metrics_aggregation_interval": 60
       }
    }
  }
}
CLOUDWATCH_EOF

echo "Moving configuration file to /opt/cloudwatch-config.json..."
sudo mv /tmp/cloudwatch-config.json /opt/cloudwatch-config.json

# Step 3: Create the log file /var/log/csye6225.log
echo "Creating log file /var/log/csye6225.log..."
sudo touch /var/log/csye6225.log

# Step 4: Reload the system daemon
echo "Reloading system daemon..."
sudo systemctl daemon-reload


# Install Python packages
sudo python3 -m pip install gunicorn boto3 watchtower statsd

# Clean up
sudo apt-get clean
sudo rm -rf /var/lib/apt/lists/*
rm -f amazon-cloudwatch-agent.deb