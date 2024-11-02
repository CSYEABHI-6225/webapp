# test_integration.py
import os
import pytest
from unittest.mock import patch, MagicMock
import json

# Set test environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_BUCKET_NAME'] = 'test-bucket'

# Create patches
aws_patches = [
    patch('boto3.client'),
    patch('boto3.Session'),
    patch('watchtower.CloudWatchLogHandler')
]

# Start patches before importing webapp
[p.start() for p in aws_patches]
from webapp import app, db, User

@pytest.fixture(scope='session', autouse=True)
def stop_patches():
    yield
    # Stop patches after all tests
    [p.stop() for p in aws_patches]

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        
    with app.test_client() as client:
        yield client
        
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture
def mock_aws():
    with patch('boto3.client') as mock_client:
        # Configure mock responses
        mock_s3 = MagicMock()
        mock_logs = MagicMock()
        
        mock_client.side_effect = lambda service, region_name=None: {
            's3': mock_s3,
            'logs': mock_logs
        }.get(service, MagicMock())
        
        yield {
            's3': mock_s3,
            'logs': mock_logs,
            'client': mock_client
        }

def test_health_check(client):
    response = client.get('/healthz')
    assert response.status_code == 200

def test_create_user(client, mock_aws):
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
    
    # Verify user was created in database
    with app.app_context():
        user = User.query.filter_by(email="john@example.com").first()
        assert user is not None
        assert user.first_name == "John"
        assert user.last_name == "Doe"

def test_create_user_invalid_data(client, mock_aws):
    data = {
        "first_name": "John123",  # Invalid name
        "last_name": "Doe",
        "email": "invalid_email",  # Invalid email
        "password": "short"  # Invalid password
    }
    
    response = client.post('/v1/user', 
                          data=json.dumps(data),
                          content_type='application/json')
    
    assert response.status_code == 400

if __name__ == '__main__':
    pytest.main(['-v'])