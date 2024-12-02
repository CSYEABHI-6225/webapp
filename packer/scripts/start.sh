#!/bin/bash

# Set up Python virtual environment
cd /opt/csye6225/webapp
source venv/bin/activate


# Handle database migrations
if [ -d "migrations" ]; then
    echo "Removing existing migrations"
    rm -rf migrations
fi

# Initialize fresh migrations
echo "Initializing fresh database migrations"
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Start the Flask application
python3 webapp.py