import os
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

import unittest
from unittest.mock import patch, MagicMock
from webapp import app, db, User, validate_email, validate_name, validate_password  # Import the validation functions

class TestValidators(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        
        # Mock AWS services
        self.aws_patch = patch('boto3.client')
        self.aws_mock = self.aws_patch.start()
        self.cloudwatch_patch = patch('watchtower.CloudWatchLogHandler')
        self.cloudwatch_mock = self.cloudwatch_patch.start()
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()
        
        # Stop AWS mocks
        self.aws_patch.stop()
        self.cloudwatch_patch.stop()

    def test_validate_email(self):
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid_email"))

    def test_validate_name(self):
        self.assertTrue(validate_name("John"))
        self.assertFalse(validate_name("John123"))

    def test_validate_password(self):
        self.assertTrue(validate_password("password123"))
        self.assertFalse(validate_password("short"))

    def test_user_password(self):
        with app.app_context():
            user = User(
                first_name="Test",
                last_name="User",
                email="test@example.com"
            )
            user.set_password('password123')
            self.assertTrue(user.check_password('password123'))
            self.assertFalse(user.check_password('wrongpassword'))

if __name__ == '__main__':
    unittest.main()