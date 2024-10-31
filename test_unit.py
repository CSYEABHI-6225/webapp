import os
os.environ['TESTING'] = 'True'  # Set this before importing webapp

import unittest
from webapp import app, db, User
from webapp import validate_email, validate_name, validate_password

class TestValidators(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        with app.app_context():
            db.create_all()

    # ... rest of your test cases ...

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