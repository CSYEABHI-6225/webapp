import os
import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_aws():
    with patch('boto3.client'), \
         patch('boto3.Session'), \
         patch('watchtower.CloudWatchLogHandler'):
        yield