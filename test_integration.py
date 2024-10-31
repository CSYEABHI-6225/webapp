import os
import pytest
from unittest.mock import patch, MagicMock

# Mock AWS services before importing webapp
with patch('boto3.client'), \
     patch('boto3.Session'), \
     patch('watchtower.CloudWatchLogHandler'):
    from webapp import app, db, User
import json

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