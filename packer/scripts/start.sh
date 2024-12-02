#!/bin/bash

# Set up Python virtual environment
cd /opt/csye6225/webapp
source venv/bin/activate

# Wait for database to be available
max_retries=30
counter=0
while ! mysql -h "$DB_HOST" -u "$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1" >/dev/null 2>&1; do
    if [ $counter -eq $max_retries ]; then
        echo "Failed to connect to database after $max_retries attempts"
        exit 1
    fi
    echo "Waiting for database connection... attempt $counter"
    sleep 10
    ((counter++))
done

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