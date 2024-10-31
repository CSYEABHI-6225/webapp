import os
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

from flask import json
import pytest
from unittest.mock import patch, MagicMock

# Create mock objects
mock_watchtower = MagicMock()
mock_boto3 = MagicMock()

# Apply mocks before importing webapp
with patch.dict('sys.modules', {
    'watchtower': mock_watchtower,
    'boto3': mock_boto3
}):
    from webapp import app, db, User

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
    yield app.test_client()
    with app.app_context():
        db.session.remove()
        db.drop_all()

def test_health_check(client):
    response = client.get('/healthz')
    assert response.status_code == 200

def test_create_user(client):
    data = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "password": "password123"
    }
    response = client.post('/v1/user', 
                          data=json.dumps(data),
                          content_type='application/json')
    assert response.status_code == 201