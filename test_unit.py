import os
os.environ['TESTING'] = 'True'
os.environ['AWS_REGION'] = 'us-east-1'

import unittest
from webapp import app, db, User
from webapp import validate_email, validate_name, validate_password

class TestValidators(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['TESTING'] = True
        with app.app_context():
            db.create_all()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_validate_email(self):
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid_email"))

    def test_validate_name(self):
        self.assertTrue(validate_name("John"))
        self.assertFalse(validate_name("John123"))

    def test_validate_password(self):
        self.assertTrue(validate_password("password123"))
        self.assertFalse(validate_password("short"))

if __name__ == '__main__':
    unittest.main()