import base64
import os
import pytest
from unittest.mock import patch, MagicMock
import json
from datetime import datetime, timezone, timedelta
import uuid
import boto3

# Set test environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_BUCKET_NAME'] = 'test-bucket'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

# Create mock objects
mock_sns = MagicMock()
mock_s3 = MagicMock()
mock_logs = MagicMock()

# Configure mock responses
mock_sns.publish.return_value = {'MessageId': 'test-message-id'}

# Create patches
patches = [
    patch('boto3.client', side_effect=lambda service, **kwargs: {
        'sns': mock_sns,
        's3': mock_s3,
        'logs': mock_logs
    }.get(service, MagicMock())),
    patch('webapp.sns_client', mock_sns),
    patch('webapp.s3_client', mock_s3),
    patch('webapp.logs_client', mock_logs),
    patch('webapp.SNS_TOPIC_ARN', 'test-topic-arn')
]

# Start patches before importing webapp
for p in patches:
    p.start()

# Import webapp after patches
from webapp import app, db, User

@pytest.fixture(scope='session', autouse=True)
def stop_patches():
    yield
    for p in patches:
        p.stop()

@pytest.fixture
def client():
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

@pytest.fixture
def mock_aws():
    # Create mock clients
    mock_sns = MagicMock()
    mock_s3 = MagicMock()
    mock_logs = MagicMock()
    
    # Configure mock responses
    mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
    
    # Create patches
    patches = [
        patch('boto3.client', return_value=mock_sns),
        patch('webapp.sns_client', new=mock_sns),
        patch('webapp.s3_client', new=mock_s3),
        patch('webapp.logs_client', new=mock_logs),
        patch('webapp.SNS_TOPIC_ARN', new='test-topic-arn')
    ]
    
    # Start all patches
    for p in patches:
        p.start()
    
    yield {
        's3': mock_s3,
        'logs': mock_logs,
        'sns': mock_sns
    }
    
    # Stop all patches
    for p in patches:
        p.stop()

@pytest.fixture
def create_test_user(client):
    with client.application.app_context():
        user = User(
            id=str(uuid.uuid4()),
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            is_verified=False
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user.id

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
                          json=data,
                          content_type='application/json')
    
    assert response.status_code == 201
    
    with client.application.app_context():
        user = User.query.filter_by(email="john@example.com").first()
        assert user is not None
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert not user.is_verified

def test_create_user_sns_publish(client, mock_aws):
    # Create patches for both boto3.client and webapp's sns_client
    with patch('boto3.client', return_value=mock_aws['sns']), \
         patch('webapp.sns_client', new=mock_aws['sns']), \
         patch('webapp.SNS_TOPIC_ARN', new='test-topic-arn'), \
         patch('webapp.TESTING', new=False):  # This is important
        
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "password123"
        }
        
        # Reset mock before test
        mock_aws['sns'].publish.reset_mock()
        
        response = client.post('/v1/user', 
                             json=data,
                             content_type='application/json')
        
        assert response.status_code == 201
        
        # Verify SNS publish was called
        mock_aws['sns'].publish.assert_called_once()
        
        # Verify the SNS message content
        call_args = mock_aws['sns'].publish.call_args
        assert call_args is not None
        kwargs = call_args[1]
        
        # Verify the SNS message format
        assert 'TopicArn' in kwargs
        assert kwargs['TopicArn'] == 'test-topic-arn'
        assert 'Message' in kwargs
        
        message = json.loads(kwargs['Message'])
        assert message['email'] == data['email']
        assert message['first_name'] == data['first_name']
        assert message['last_name'] == data['last_name']

def test_protected_routes_verification(client, create_test_user):
    auth_str = base64.b64encode(
        b"john@example.com:password123").decode()
    headers = {'Authorization': f'Basic {auth_str}'}
    
    protected_routes = [
        ('GET', '/v1/user/self'),
        ('PUT', '/v1/user/self'),
        ('POST', '/v1/user/self/pic'),
        ('GET', '/v1/user/self/pic'),
        ('DELETE', '/v1/user/self/pic')
    ]
    
    for method, route in protected_routes:
        response = client.open(
            route,
            method=method,
            headers=headers
        )
        assert response.status_code == 403
        error_data = json.loads(response.data)
        assert error_data['error'] == 'Email verification required'

def test_verified_user_access(client, create_test_user):
    with client.application.app_context():
        user = db.session.get(User, create_test_user)
        user.is_verified = True
        db.session.commit()
    
    auth_str = base64.b64encode(
        b"john@example.com:password123").decode()
    headers = {'Authorization': f'Basic {auth_str}'}
    
    response = client.get('/v1/user/self', headers=headers)
    assert response.status_code == 200

def test_verification_token_expiry(client, create_test_user):
    with client.application.app_context():
        user = db.session.get(User, create_test_user)
        
        # Create timezone-aware datetime without microseconds
        current_time = datetime.now(timezone.utc).replace(microsecond=0)
        expiry_time = current_time - timedelta(minutes=3)
        
        user.verification_token = "test_token"
        user.token_expiry = expiry_time
        db.session.commit()
        
        # Query again to get fresh data
        user = db.session.get(User, create_test_user)
        stored_time = user.token_expiry.replace(tzinfo=timezone.utc)
        
        assert stored_time < current_time
        assert not user.is_verified

def test_create_user_invalid_data(client):
    invalid_data_cases = [
        {
            "first_name": "John123",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "password123"
        },
        {
            "first_name": "John",
            "last_name": "Doe123",
            "email": "john@example.com",
            "password": "password123"
        },
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid_email",
            "password": "password123"
        },
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "password": "short"
        }
    ]
    
    for data in invalid_data_cases:
        response = client.post('/v1/user', 
                             json=data,
                             content_type='application/json')
        assert response.status_code == 400

if __name__ == '__main__':
    pytest.main(['-v'])