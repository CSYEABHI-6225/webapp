from flask import Flask, request, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import os
from sqlalchemy import text

app = Flask(__name__)
print(os.getenv('SQLALCHEMY_DATABASE_URI'))
# Configure the database connection using SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
auth = HTTPBasicAuth()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.Text)
    account_created = db.Column(db.DateTime, default=datetime.utcnow)
    account_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_name(name):
    return name.isalpha()

def validate_password(password):
    return len(password) >= 8

@auth.verify_password
def verify_password(email, password):
    if not email or not password:
        return None
    if not validate_email(email):
        return None
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user
    return None

def check_queryparam() -> bool:
    return bool(request.args)

def check_db_connection() -> bool:
    """Check if the application can connect to the database."""
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(e)
        return False

@app.route('/healthz', methods=['GET'])
def health_check():

    if check_queryparam():
        return '', 404


    if request.data:
        return '', 400


    if check_db_connection():
        return jsonify({"status": "healthy"}), 200
    else:
        return '', 503 

@app.route('/v1/user', methods=['POST'])
def create_user():
    try:

        if check_queryparam():
            return '', 404

        data = request.json
        if not data:
            return '', 400

        # Validate input data
        if not all(key in data for key in ('first_name', 'last_name', 'email', 'password')):
            return '', 400

        if not validate_name(data['first_name']):
            return '', 400

        if not validate_name(data['last_name']):
            return '', 400

        if not validate_email(data['email']):
            return '', 400

        if not validate_password(data['password']):
            return '', 400

        if User.query.filter_by(email=data['email']).first():
            return '', 400
        
        new_user = User(
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email']
        )
        new_user.set_password(data['password'])
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            "id": new_user.id,
            "first_name": new_user.first_name,
            "last_name": new_user.last_name,
            "email": new_user.email,
            "account_created": new_user.account_created.isoformat(),
            "account_updated": new_user.account_updated.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return '', 500

@app.route('/v1/user/self', methods=['PUT'])
@auth.login_required
def update_user():

    if check_queryparam():
        return '', 404

    user = auth.current_user()
    data = request.json
    
    if 'first_name' in data:
        if not validate_name(data['first_name']):
            return '', 400
        user.first_name = data['first_name']
    if 'last_name' in data:
        if not validate_name(data['last_name']):
            return '', 400
        user.last_name = data['last_name']
    if 'password' in data:
        if not validate_password(data['password']):
            return '', 400
        user.set_password(data['password'])
    
    db.session.commit()
    
    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "account_created": user.account_created.isoformat(),
        "account_updated": user.account_updated.isoformat()
    }), 200

@app.route('/v1/user/self', methods=['GET'])
@auth.login_required
def get_user():

    if check_queryparam():
        return '', 404

    if request.data:
        return '', 400

    user = auth.current_user()
    return jsonify({
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "account_created": user.account_created.isoformat(),
        "account_updated": user.account_updated.isoformat()
    }), 200


@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache'
    return response

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)