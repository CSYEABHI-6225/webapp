# test_unit.py
import os
import unittest
from unittest.mock import patch, MagicMock

# Set test environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_BUCKET_NAME'] = 'test-bucket'

class TestValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Mock AWS services before importing webapp
        cls.patches = [
            patch('boto3.client'),
            patch('boto3.Session'),
            patch('watchtower.CloudWatchLogHandler')
        ]
        cls.mocks = [p.start() for p in cls.patches]
        
        # Import webapp after mocking AWS services
        from webapp import app, db, User, validate_email, validate_name, validate_password
        cls.app = app
        cls.db = db
        cls.User = User
        cls.validate_email = staticmethod(validate_email)
        cls.validate_name = staticmethod(validate_name)
        cls.validate_password = staticmethod(validate_password)

    @classmethod
    def tearDownClass(cls):
        # Stop all patches
        for p in cls.patches:
            p.stop()

    def setUp(self):
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        
        with self.app.app_context():
            self.db.create_all()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()

    def test_validate_email(self):
        self.assertTrue(self.validate_email("test@example.com"))
        self.assertFalse(self.validate_email("invalid_email"))

    def test_validate_name(self):
        self.assertTrue(self.validate_name("John"))
        self.assertFalse(self.validate_name("John123"))

    def test_validate_password(self):
        self.assertTrue(self.validate_password("password123"))
        self.assertFalse(self.validate_password("short"))

    def test_user_password(self):
        with self.app.app_context():
            user = self.User(
                first_name="Test",
                last_name="User",
                email="test@example.com"
            )
            user.set_password('password123')
            self.assertTrue(user.check_password('password123'))
            self.assertFalse(user.check_password('wrongpassword'))

if __name__ == '__main__':
    unittest.main()