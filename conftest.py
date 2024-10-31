import os
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_aws():
    """Mock AWS services for all tests"""
    mock_watchtower = MagicMock()
    mock_boto3 = MagicMock()
    
    with patch.dict('sys.modules', {
        'watchtower': mock_watchtower,
        'boto3': mock_boto3
    }):
        yield

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ['TESTING'] = 'True'
    os.environ['AWS_REGION'] = 'us-east-1'