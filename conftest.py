import os
import pytest

@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ['TESTING'] = 'True'
    os.environ['AWS_REGION'] = 'us-east-1'