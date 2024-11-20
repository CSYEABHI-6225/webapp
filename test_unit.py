import base64
import os
import uuid
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from flask_migrate import Migrate

# Set test environment variables
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'
os.environ['AWS_BUCKET_NAME'] = 'test-bucket'
os.environ['SNS_TOPIC_ARN'] = 'arn:aws:sns:us-east-1:123456789012:test-topic'

class TestValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create mock objects
        cls.mock_sns = MagicMock()
        cls.mock_s3 = MagicMock()
        cls.mock_cloudwatch = MagicMock()
        cls.mock_statsd = MagicMock()
        
        # Configure mock responses
        cls.mock_sns.publish.return_value = {'MessageId': 'test-message-id'}
        
        # Create patches
        cls.patches = [
            patch('boto3.client'),
            patch('boto3.Session'),
            patch('watchtower.CloudWatchLogHandler'),
            patch('statsd.StatsClient', return_value=cls.mock_statsd)
        ]
        
        # Start patches
        cls.mocks = [p.start() for p in cls.patches]
        
        # Configure boto3.client mock
        def mock_boto3_client(service, *args, **kwargs):
            if service == 'sns':
                return cls.mock_sns
            elif service == 's3':
                return cls.mock_s3
            elif service == 'logs':
                return cls.mock_cloudwatch
            return MagicMock()
        
        cls.mocks[0].side_effect = mock_boto3_client
        
        # Import webapp after mocking
        from webapp import app, db, User, validate_email, validate_name, validate_password
        cls.app = app
        cls.db = db
        cls.User = User
        cls.validate_email = staticmethod(validate_email)
        cls.validate_name = staticmethod(validate_name)
        cls.validate_password = staticmethod(validate_password)

    def setUp(self):
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        
        with self.app.app_context():
            self.db.create_all()

    def tearDown(self):
        with self.app.app_context():
            self.db.session.remove()
            self.db.drop_all()

    @classmethod
    def tearDownClass(cls):
        for p in cls.patches:
            p.stop()

    # Existing test methods remain unchanged

    def test_user_creation_with_sns(self):
        """Test user creation with SNS notification"""
        with self.app.test_client() as client:
            data = {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john@example.com",
                "password": "password123"
            }
            
            response = client.post('/v1/user', 
                                 json=data,
                                 content_type='application/json')
            
            self.assertEqual(response.status_code, 201)
            
            # Verify user was created
            with self.app.app_context():
                user = self.User.query.filter_by(email="john@example.com").first()
                self.assertIsNotNone(user)
                self.assertFalse(user.is_verified)

    def test_protected_routes_verification(self):
        """Test protected routes with verification requirement"""
        with self.app.app_context():
            # Create test user
            user = self.User(
                id=str(uuid.uuid4()),
                first_name="Test",
                last_name="User",
                email="test@example.com",
                is_verified=False
            )
            user.set_password('password123')
            self.db.session.add(user)
            self.db.session.commit()

            with self.app.test_client() as client:
                auth_str = base64.b64encode(
                    f"{user.email}:password123".encode()
                ).decode()
                headers = {'Authorization': f'Basic {auth_str}'}

                # Test protected route with unverified user
                response = client.get('/v1/user/self', headers=headers)
                self.assertEqual(response.status_code, 403)
                
                # Verify user and test again
                user.is_verified = True
                self.db.session.commit()
                
                response = client.get('/v1/user/self', headers=headers)
                self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()