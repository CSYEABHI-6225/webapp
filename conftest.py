import os
import pytest
from unittest.mock import MagicMock, patch

@pytest.fixture(autouse=True)
def mock_aws():
    # Create mock SNS client
    mock_sns = MagicMock()
    mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
    
    # Create mock S3 client
    mock_s3 = MagicMock()
    mock_s3.upload_fileobj.return_value = None
    mock_s3.delete_object.return_value = None
    
    # Create mock CloudWatch client
    mock_cloudwatch = MagicMock()
    
    # Create the mock client function
    def mock_boto3_client(service_name, *args, **kwargs):
        if service_name == 'sns':
            return mock_sns
        elif service_name == 's3':
            return mock_s3
        elif service_name == 'logs':
            return mock_cloudwatch
        return MagicMock()

    # Apply patches
    with patch('boto3.client') as mock_client, \
         patch('boto3.Session'), \
         patch('watchtower.CloudWatchLogHandler'):
        
        mock_client.side_effect = mock_boto3_client
        yield {
            'sns': mock_sns,
            's3': mock_s3,
            'cloudwatch': mock_cloudwatch,
            'client': mock_client
        }

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    test_env_vars = {
        'TESTING': 'True',
        'AWS_REGION': 'us-east-1',
        'AWS_BUCKET_NAME': 'test-bucket',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SNS_TOPIC_ARN': 'arn:aws:sns:us-east-1:123456789012:test-topic',
        'HOSTNAME': 'localhost'
    }
    
    # Store original environment variables
    original_env = {}
    for key in test_env_vars:
        original_env[key] = os.environ.get(key)
        os.environ[key] = test_env_vars[key]
    
    yield
    
    # Restore original environment variables
    for key, value in original_env.items():
        if value is None:
            del os.environ[key]
        else:
            os.environ[key] = value

@pytest.fixture
def app():
    """Create test Flask application."""
    from webapp import app, db
    
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def db(app):
    """Create test database."""
    from webapp import db
    return db