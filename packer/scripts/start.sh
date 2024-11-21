#!/bin/bash
set -e

source /opt/csye6225/webapp/venv/bin/activate
flask db init || true
flask db migrate -m "Added new column to User model"
flask db upgrade
python3 webapp.py