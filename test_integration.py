import os
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

import pytest
from unittest.mock import patch, MagicMock
import json

# Mock AWS services before importing webapp
mock_boto3 = MagicMock()
mock_watchtower = MagicMock()

with patch.dict('sys.modules', {
    'boto3': mock_boto3,
    'watchtower': mock_watchtower
}):
    from webapp import app, db, User

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        # Create all tables
        db.create_all()
        yield app.test_client()
        # Clean up
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