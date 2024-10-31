import unittest
from unittest.mock import patch, MagicMock
from webapp import app, db, User
from webapp import validate_email, validate_name, validate_password
from werkzeug.security import generate_password_hash, check_password_hash

class TestValidators(unittest.TestCase):
    @patch('boto3.client')
    @patch('watchtower.CloudWatchLogHandler')
    def setUp(self, mock_cloudwatch, mock_boto):
        # Mock AWS services
        self.mock_boto = mock_boto
        self.mock_cloudwatch = mock_cloudwatch
        
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['AWS_REGION'] = 'us-east-1'
        app.config['AWS_ACCESS_KEY'] = 'test-key'
        app.config['AWS_SECRET_KEY'] = 'test-secret'
        app.config['AWS_BUCKET_NAME'] = 'test-bucket'
        
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()


    def test_set_password(self):
        with app.app_context():  # Create an application context
            user = User(email='test@example.com')
            user.set_password('password123')
            self.assertTrue(check_password_hash(user.password_hash, 'password123'))

    def test_check_password(self):
        with app.app_context():  # Create an application context
            user = User(email='test@example.com')
            user.set_password('password123')
            self.assertTrue(user.check_password('password123'))
            self.assertFalse(user.check_password('wrongpassword'))

if __name__ == '__main__':
    unittest.main()