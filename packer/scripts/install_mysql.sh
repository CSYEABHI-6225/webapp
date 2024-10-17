#!/bin/bash
set -e  # Exit immediately if a command exits with a non-zero status
set -u  # Treat unset variables as an error and exit immediately
set -x  # Enable debug mode

# Update package lists
echo "Updating package lists..."
sudo apt-get update

# Install MySQL Server
echo "Installing MySQL Server..."
sudo apt-get install -y mysql-server

# Run MySQL secure installation
echo "Running MySQL secure installation..."
sudo mysql_secure_installation <<EOF
n
y
y
y
y
EOF

# Start and enable MySQL service
echo "Starting and enabling MySQL service..."
sudo systemctl start mysql
sudo systemctl enable mysql

# Check if MySQL service is running
echo "Checking if MySQL service is running..."
if sudo systemctl status mysql | grep -q "active (running)"; then
    echo "MySQL service is running."
else
    echo "MySQL service is not running. Exiting."
    exit 1
fi

# Load environment variables from .env file
if [ -f /tmp/webapp/.env ]; then
    # Clean the .env file to remove carriage returns
    tr -d '\r' < /tmp/webapp/.env > /tmp/webapp/.env.cleaned
    mv /tmp/webapp/.env.cleaned /tmp/webapp/.env
    source /tmp/webapp/.env
    echo "Loaded environment variables from .env file:"
    cat /tmp/webapp/.env
else
    echo "Error: .env file not found in /tmp/webapp/!"
    exit 1
fi

# Create MySQL database and user
echo "Creating MySQL database and user..."
sudo mysql -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"
sudo mysql -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';"
sudo mysql -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';"
sudo mysql -e "FLUSH PRIVILEGES;"

# Verify database creation
echo "Verifying database creation..."
if sudo mysql -e "SHOW DATABASES;" | grep -q "${DB_NAME}"; then
    echo "Database ${DB_NAME} created successfully."
else
    echo "Failed to create database ${DB_NAME}."
    exit 1
fi

# Verify user creation
echo "Verifying user creation..."
if sudo mysql -e "SELECT User FROM mysql.user;" | grep -q "${DB_USER}"; then
    echo "User ${DB_USER} created successfully."
else
    echo "Failed to create user ${DB_USER}."
    exit 1
fi
