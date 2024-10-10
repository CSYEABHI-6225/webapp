import unittest
from webapp import app, db, User
from webapp import validate_email, validate_name, validate_password
from werkzeug.security import generate_password_hash, check_password_hash

class TestValidators(unittest.TestCase):
    def test_validate_email(self):
        self.assertTrue(validate_email("test@example.com"))
        self.assertFalse(validate_email("invalid_email"))

    def test_validate_name(self):
        self.assertTrue(validate_name("John"))
        self.assertFalse(validate_name("John123"))

    def test_validate_password(self):
        self.assertTrue(validate_password("password123"))
        self.assertFalse(validate_password("short"))

class TestUserModel(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # Set database URI here
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