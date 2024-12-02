#!/bin/bash

# Set up Python virtual environment
cd /opt/csye6225/webapp
source venv/bin/activate


# Handle database migrations
if [ -d "migrations" ]; then
    echo "Running database upgrade"
    flask db upgrade
else
    echo "Initializing database"
    flask db init
    flask db migrate -m "Initial migration"
    flask db upgrade
fi

# Start the Flask application
python3 webapp.py