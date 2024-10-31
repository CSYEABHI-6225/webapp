import os
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_aws():
    """Mock AWS services for all tests"""
    with patch('boto3.client'), \
         patch('boto3.Session'), \
         patch('watchtower.CloudWatchLogHandler'):
        yield

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ['TESTING'] = 'True'
    os.environ['AWS_REGION'] = 'us-east-1'