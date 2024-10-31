import os
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

import unittest
from unittest.mock import patch, MagicMock
import json

# Mock AWS services before importing webapp
mock_boto3 = MagicMock()
mock_watchtower = MagicMock()

with patch.dict('sys.modules', {
    'boto3': mock_boto3,
    'watchtower': mock_watchtower
}):
    from webapp import app, db, User, validate_email, validate_name, validate_password

class TestValidators(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        self.app = app.test_client()
        with app.app_context():
            # Create all tables
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_validate_email(self):
        """Test email validation"""
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid_email"))

    def test_validate_name(self):
        """Test name validation"""
        self.assertTrue(validate_name("John"))
        self.assertFalse(validate_name("John123"))

    def test_validate_password(self):
        """Test password validation"""
        self.assertTrue(validate_password("password123"))
        self.assertFalse(validate_password("short"))

if __name__ == '__main__':
    unittest.main()