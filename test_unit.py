import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Set testing environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

# Create mock modules
mock_watchtower = MagicMock()
mock_boto3 = MagicMock()

# Mock AWS services before importing webapp
with patch.dict('sys.modules', {
    'watchtower': mock_watchtower,
    'boto3': mock_boto3
}):
    from webapp import app, db, User, validate_email, validate_name, validate_password

class TestValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test database once for all tests"""
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
    def setUp(self):
        """Set up test database for each test"""
        self.app = app.test_client()
        with app.app_context():
            db.create_all()

    def tearDown(self):
        """Clean up after each test"""
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