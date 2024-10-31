import os
import sys
import pytest
from unittest.mock import MagicMock

# Create mock modules
mock_watchtower = MagicMock()
mock_boto3 = MagicMock()

# Register mocks
sys.modules['watchtower'] = mock_watchtower
sys.modules['boto3'] = mock_boto3

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ['TESTING'] = 'True'
    os.environ['AWS_REGION'] = 'us-east-1'