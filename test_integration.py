import os
import sys
import pytest
from unittest.mock import patch, MagicMock
import json

# Set testing environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

# Create mock modules
mock_watchtower = MagicMock()
mock_boto3 = MagicMock()

# Mock AWS services before importing webapp
with patch.dict('sys.modules', {
    'watchtower': mock_watchtower,
    'boto3': mock_boto3
}):
    from webapp import app, db, User

@pytest.fixture(scope='function')
def client():
    """Create a test client"""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.session.remove()
            db.drop_all()

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/healthz')
    assert response.status_code == 200

def test_create_user(client):
    """Test user creation"""
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "password": "password123"
    }
    response = client.post(
        '/v1/user',
        data=json.dumps(data),
        content_type='application/json'
    )
    assert response.status_code == 201