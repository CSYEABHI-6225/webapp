import os
import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_aws():
    """Mock AWS services for all tests"""
    mock_boto3 = MagicMock()
    mock_watchtower = MagicMock()
    
    with patch.dict('sys.modules', {
        'boto3': mock_boto3,
        'watchtower': mock_watchtower
    }):
        yield

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables"""
    os.environ['TESTING'] = 'True'
    os.environ['AWS_REGION'] = 'us-east-1'