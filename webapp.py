from flask import Flask, json, request, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import text
from logging.handlers import RotatingFileHandler
from functools import wraps
import re
import os
import uuid
import logging
import boto3
from botocore.exceptions import ClientError
import watchtower
import statsd
import time

# Create logs directory if it doesn't exist
if not os.path.exists('logs'):
    os.makedirs('logs')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create handlers
console_handler = logging.StreamHandler()
file_handler = RotatingFileHandler('logs/webapp.log', maxBytes=10000, backupCount=3)

# Create formatters and add it to handlers
log_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(log_format)
file_handler.setFormatter(log_format)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Load environment variables
load_dotenv()

def verify_env_vars():
    required_vars = [
        'SQLALCHEMY_DATABASE_URI',
        'AWS_REGION',
        'AWS_BUCKET_NAME',
        'HOSTNAME'
    ]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

verify_env_vars()

# Check if we're in test mode
TESTING = os.getenv('TESTING', 'False').lower() == 'true'

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['HOSTNAME'] = os.getenv('HOSTNAME')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# AWS Configuration
app.config['AWS_REGION'] = os.getenv('AWS_REGION', 'us-east-1')
app.config['AWS_BUCKET_NAME'] = os.getenv('AWS_BUCKET_NAME')

db = SQLAlchemy(app)
auth = HTTPBasicAuth()
migrate = Migrate(app, db)

# Configure StatsD for metrics
statsd_client = statsd.StatsClient('localhost', 8125)

# Initialize AWS services only if not in testing mode

sns_client = None
s3_client = None
logs_client = None
SNS_TOPIC_ARN = None

if not TESTING:
    try:
        # Initialize AWS clients
        logs_client = boto3.client('logs', region_name=app.config['AWS_REGION'])
        s3_client = boto3.client('s3', region_name=app.config['AWS_REGION'])
        
        # SNS Client initialization
        sns_client = boto3.client('sns', region_name=app.config['AWS_REGION'])
        SNS_TOPIC_ARN = os.getenv('SNS_TOPIC_ARN')
        
        # Configure CloudWatch logging
        cloudwatch_handler = watchtower.CloudWatchLogHandler(
            log_group='csye6225',
            stream_name='webapp',
            boto3_client=logs_client
        )
        
        # Add handler to logger
        logger.addHandler(cloudwatch_handler)
        
    except Exception as e:
        logger.error(f"Failed to initialize AWS services: {e}")
else:
    s3_client = None
    SNS_TOPIC_ARN = None

def verify_database():
    try:
        with statsd_client.timer('database.connection.timing'):
            with app.app_context():
                db.session.execute(text('SELECT 1'))
        statsd_client.incr('database.connection.success')
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        statsd_client.incr('database.connection.error')
        return False

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(36), primary_key=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    account_created = db.Column(db.DateTime, default=datetime.utcnow)
    account_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100))
    token_expiry = db.Column(db.DateTime)
    images = db.relationship('Image', backref='user', lazy=True, cascade="all, delete-orphan")
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Image(db.Model):
    __tablename__ = 'image'
    file_name = db.Column(db.String(255), nullable=False)
    id = db.Column(db.String(36), primary_key=True)
    url = db.Column(db.String(512), nullable=False)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.String(36), db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)

def validate_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def validate_name(name):
    return name.isalpha()

def validate_password(password):
    return len(password) >= 8

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@auth.verify_password
def verify_password(email, password):
    statsd_client.incr('auth.attempt')
    if not email or not password:
        statsd_client.incr('auth.invalid_input')
        return None
    if not validate_email(email):
        return None
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        statsd_client.incr('auth.success')
        return user
    statsd_client.incr('auth.failure')
    return None

def check_queryparam():
    return bool(request.args)

def check_db_connection():
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception:
        logger.error("Database connection failed")
        return False

def require_verification(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = auth.current_user()
        if not user.is_verified:
            return '', 403
        return f(*args, **kwargs)
    return decorated_function


@app.route('/healthz', methods=['GET'])
def health_check():
    logger.info("GET /healthz - Health check request received")
    statsd_client.incr('endpoint.healthcheck.attempt')
    
    with statsd_client.timer('endpoint.healthcheck.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.healthcheck.error.query_param')
            return '', 404

        if request.data:
            statsd_client.incr('endpoint.healthcheck.error.request_data')
            return '', 400

        try:
            with statsd_client.timer('endpoint.healthcheck.db.timing'):
                db_healthy = check_db_connection()
            
            if db_healthy:
                statsd_client.incr('endpoint.healthcheck.success')
                return '', 200
            else:
                statsd_client.incr('endpoint.healthcheck.error.db_connection')
                return '', 503
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            statsd_client.incr('endpoint.healthcheck.error')
            return '', 503

@app.route('/healthzsssss', methods=['GET'])
def health_check():
    logger.info("GET /healthz - Health check request received")
    statsd_client.incr('endpoint.healthcheck.attempt')
    
    with statsd_client.timer('endpoint.healthcheck.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.healthcheck.error.query_param')
            return '', 404

        if request.data:
            statsd_client.incr('endpoint.healthcheck.error.request_data')
            return '', 400

        try:
            with statsd_client.timer('endpoint.healthcheck.db.timing'):
                db_healthy = check_db_connection()
            
            if db_healthy:
                statsd_client.incr('endpoint.healthcheck.success')
                return '', 200
            else:
                statsd_client.incr('endpoint.healthcheck.error.db_connection')
                return '', 503
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            statsd_client.incr('endpoint.healthcheck.error')
            return '', 503

@app.route('/cicd', methods=['GET'])
def health_check():
    logger.info("GET /healthz - Health check request received")
    statsd_client.incr('endpoint.healthcheck.attempt')
    
    with statsd_client.timer('endpoint.healthcheck.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.healthcheck.error.query_param')
            return '', 404

        if request.data:
            statsd_client.incr('endpoint.healthcheck.error.request_data')
            return '', 400

        try:
            with statsd_client.timer('endpoint.healthcheck.db.timing'):
                db_healthy = check_db_connection()
            
            if db_healthy:
                statsd_client.incr('endpoint.healthcheck.success')
                return '', 200
            else:
                statsd_client.incr('endpoint.healthcheck.error.db_connection')
                return '', 503
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            statsd_client.incr('endpoint.healthcheck.error')
            return '', 503

@app.route('/v1/user', methods=['POST'])
def create_user():
    logger.info("POST /v1/user - Create user request received")
    statsd_client.incr('endpoint.user.create.attempt')
    try:
        if check_queryparam():
            return '', 404

        data = request.json
        if not data:
            return '', 400

        required_keys = ('first_name', 'last_name', 'email', 'password')
        if not all(key in data for key in required_keys):
            return '', 400

        if not validate_name(data['first_name']) or not validate_name(data['last_name']):
            return '', 400

        if not validate_email(data['email']):
            return '', 400

        if not validate_password(data['password']):
            return '', 400

        if User.query.filter_by(email=data['email']).first():
            return '', 400

        new_user = User(
            id=str(uuid.uuid4()),
            first_name=data['first_name'],
            last_name=data['last_name'],
            email=data['email'],
            is_verified=False
        )
        new_user.set_password(data['password'])
        db.session.add(new_user)
        db.session.commit()
        
        statsd_client.incr('endpoint.user.create.success')
        
        secret_token = os.getenv('SECRET_TOKEN')  # Get the SECRET_TOKEN from .env
        token_data = new_user.id + secret_token
        
        verification_token = token_data
        
        new_user.verification_token = verification_token
        new_user.token_expiry = new_user.account_created + timedelta(minutes=2)
        db.session.commit()
        
         # Publish to SNS if not in testing mode
        if not TESTING  and sns_client and SNS_TOPIC_ARN:
            try:
                sns_message = {
                    'user_id': new_user.id,
                    'email': new_user.email,
                    'first_name': new_user.first_name,
                    'last_name': new_user.last_name
                }
                sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Message=json.dumps(sns_message)
                )
            except Exception as e:
                logger.error(f"SNS publish error: {str(e)}")

        # Update User model to include verification status
        new_user.is_verified = False
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
        logger.error(f"Error creating user: {str(e)}")
        statsd_client.incr('endpoint.user.create.error')
        db.session.rollback()
        return '', 500

@app.route('/v1/user/verify', methods=['GET'])
def verify_user():
    try:
        token = request.args.get('token')
        if not token:
            return '', 400

        user = User.query.filter_by(verification_token=token).first()
        if not user:
            return '', 400

        if user.is_verified:
            return '', 400

        if datetime.utcnow() > user.token_expiry:
            return '', 400

        user.is_verified = True
        user.verification_token = None  # Nullify the token after use
        db.session.commit()

        return '', 200
    except Exception as e:
        app.logger.error(f"Error verifying user: {str(e)}")
        return '', 500

@app.route('/v1/user/self', methods=['PUT'])
@auth.login_required
@require_verification
def update_user():
    logger.info("PUT /v1/user/self - Update user request received")
    statsd_client.incr('endpoint.user.update.attempt')
    
    with statsd_client.timer('endpoint.user.update.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.user.update.error.query_param')
            return '', 404

        user = auth.current_user()
        data = request.json

        if not data:
            statsd_client.incr('endpoint.user.update.error.no_data')
            return '', 400

        required_fields = ['first_name', 'last_name', 'password']
        if not all(field in data for field in required_fields):
            statsd_client.incr('endpoint.user.update.error.missing_fields')
            return '', 400

        if not validate_name(data['first_name']) or not validate_name(data['last_name']):
            statsd_client.incr('endpoint.user.update.error.invalid_name')
            return '', 400

        if not validate_password(data['password']):
            statsd_client.incr('endpoint.user.update.error.invalid_password')
            return '', 400

        try:
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.set_password(data['password'])

            with statsd_client.timer('endpoint.user.update.db.timing'):
                db.session.commit()
            
            statsd_client.incr('endpoint.user.update.success')
            return jsonify({
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "account_created": user.account_created.isoformat(),
                "account_updated": user.account_updated.isoformat()
            }), 200

        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            statsd_client.incr('endpoint.user.update.error.db')
            db.session.rollback()
            return '', 500

@app.route('/v1/user/self', methods=['GET'])
@auth.login_required
@require_verification
def get_user():
    logger.info("GET /v1/user/self - Get user request received")
    statsd_client.incr('endpoint.user.self.get.attempt')
    
    with statsd_client.timer('endpoint.user.self.get.timing'):
        try:
            if check_queryparam():
                statsd_client.incr('endpoint.user.self.get.error.query_param')
                return '', 404

            if request.data:
                statsd_client.incr('endpoint.user.self.get.error.request_data')
                return '', 400

            user = auth.current_user()
            statsd_client.incr('endpoint.user.self.get.success')
            return jsonify({
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "account_created": user.account_created.isoformat(),
                "account_updated": user.account_updated.isoformat()
            }), 200
        except Exception as e:
            statsd_client.incr('endpoint.user.self.get.error')
            return '',500

@app.route('/v1/user/self/pic', methods=['POST'])
@auth.login_required
@require_verification
def upload_profile_pic():
    logger.info("POST /v1/user/self/pic - Upload profile picture request received")
    statsd_client.incr('endpoint.user.pic.upload.attempt')
    
    with statsd_client.timer('endpoint.user.pic.upload.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.user.pic.upload.error.query_param')
            return '', 404

        if 'profilePic' not in request.files:
            statsd_client.incr('endpoint.user.pic.upload.error.no_file')
            return '', 400

        file = request.files['profilePic']
        
        if file.filename == '':
            statsd_client.incr('endpoint.user.pic.upload.error.empty_filename')
            return '', 400

        if not allowed_file(file.filename):
            statsd_client.incr('endpoint.user.pic.upload.error.invalid_extension')
            return '', 400

        try:
            # Check if user already has a profile picture
            existing_image = Image.query.filter_by(user_id=auth.current_user().id).first()
            if existing_image:
                statsd_client.incr('endpoint.user.pic.upload.error.already_exists')
                logger.warning(f"User {auth.current_user().id} already has a profile picture")
                return '', 400  # Return 400 if user already has an image

            user_id = auth.current_user().id
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            s3_key = f"{user_id}/profile.{file_extension}"

            if not TESTING:
                with statsd_client.timer('endpoint.user.pic.upload.s3.timing'):
                    s3_client.upload_fileobj(
                        file,
                        app.config['AWS_BUCKET_NAME'],
                        s3_key,
                        ExtraArgs={
                            'ContentType': f'image/{file_extension}',
                            'ACL': 'private'
                        }
                    )
                statsd_client.incr('endpoint.user.pic.upload.s3.success')

            image = Image(
                id=str(uuid.uuid4()),  # Generate a new UUID for the image
                file_name=original_filename,
                url=f"{app.config['AWS_BUCKET_NAME']}/{s3_key}",
                user_id=user_id
            )
            
            db.session.add(image)
            db.session.commit()
            statsd_client.incr('endpoint.user.pic.upload.db.success')

            return jsonify({
                "file_name": image.file_name,
                "id": image.id,
                "url": image.url,
                "upload_date": image.upload_date.strftime("%Y-%m-%d"),
                "user_id": image.user_id
            }), 201

        except Exception as e:
            logger.error(f"Error uploading profile picture: {str(e)}")
            statsd_client.incr('endpoint.user.pic.upload.error')
            db.session.rollback()
            return '', 500

@app.route('/v1/user/self/pic', methods=['GET'])
@auth.login_required
@require_verification
def get_profile_pic():
    logger.info("GET /v1/user/self/pic - Get profile picture request received")
    statsd_client.incr('endpoint.user.pic.get.attempt')
    
    with statsd_client.timer('endpoint.user.pic.get.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.user.pic.get.error.query_param')
            return '', 404

        if request.data:
            statsd_client.incr('endpoint.user.pic.get.error.request_data')
            return '', 400

        try:
            with statsd_client.timer('endpoint.user.pic.get.db.timing'):
                image = Image.query.filter_by(user_id=auth.current_user().id).first()
            
            if not image:
                statsd_client.incr('endpoint.user.pic.get.error.not_found')
                return '', 404

            statsd_client.incr('endpoint.user.pic.get.success')
            return jsonify({
                "file_name": image.file_name,
                "id": image.id,
                "url": image.url,
                "upload_date": image.upload_date.strftime("%Y-%m-%d"),
                "user_id": image.user_id
            }), 200

        except Exception as e:
            logger.error(f"Error retrieving profile picture: {str(e)}")
            statsd_client.incr('endpoint.user.pic.get.error')
            return '', 500

@app.route('/v1/user/self/pic', methods=['DELETE'])
@auth.login_required
@require_verification
def delete_profile_pic():
    logger.info("DELETE /v1/user/self/pic - Delete profile picture request received")
    statsd_client.incr('endpoint.user.pic.delete.attempt')
    
    with statsd_client.timer('endpoint.user.pic.delete.timing'):
        if check_queryparam():
            statsd_client.incr('endpoint.user.pic.delete.error.query_param')
            return '', 404

        try:
            with statsd_client.timer('endpoint.user.pic.delete.db.query.timing'):
                image = Image.query.filter_by(user_id=auth.current_user().id).first()
            
            if not image:
                statsd_client.incr('endpoint.user.pic.delete.error.not_found')
                return '', 404

            if not TESTING:
                try:
                    file_extension = image.file_name.rsplit('.', 1)[1].lower()
                    s3_key = f"{auth.current_user().id}/profile.{file_extension}"
                    
                    with statsd_client.timer('endpoint.user.pic.delete.s3.timing'):
                        s3_client.delete_object(
                            Bucket=app.config['AWS_BUCKET_NAME'],
                            Key=s3_key
                        )
                    statsd_client.incr('endpoint.user.pic.delete.s3.success')
                except ClientError as e:
                    logger.error(f"Error deleting from S3: {str(e)}")
                    statsd_client.incr('endpoint.user.pic.delete.s3.error')

            with statsd_client.timer('endpoint.user.pic.delete.db.delete.timing'):
                db.session.delete(image)
                db.session.commit()
            
            statsd_client.incr('endpoint.user.pic.delete.success')
            return '', 204

        except Exception as e:
            logger.error(f"Error deleting profile picture: {str(e)}")
            statsd_client.incr('endpoint.user.pic.delete.error')
            db.session.rollback()
            return '', 500

@app.errorhandler(405)
def method_not_allowed(e):
    logger.warning(f"Method not allowed: {request.method} {request.path}")
    statsd_client.incr('error.method_not_allowed')
    return '', 405

@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache'
    return response

@app.before_request
def log_request_info():
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Headers: {dict(request.headers)}")

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {str(e)}")
    return '', 500
if __name__ == '__main__':
    # Wait for database to be ready
    max_retries = 5
    retry_count = 0
    
    statsd_client.incr('application.startup.attempt')
    
    with statsd_client.timer('application.database.connection.timing'):
        while retry_count < max_retries:
            if verify_database():
                statsd_client.incr('application.database.connection.success')
                logger.info("Database connection successful")
                break
            
            statsd_client.incr('application.database.connection.retry')
            logger.info("Waiting for database connection...")
            time.sleep(5)
            retry_count += 1
        
        if retry_count >= max_retries:
            statsd_client.incr('application.database.connection.failure')
            logger.error("Failed to connect to database after maximum retries")
            exit(1)
    
    with app.app_context():
        try:
            with statsd_client.timer('application.database.tables.creation.timing'):
                db.create_all()
            statsd_client.incr('application.database.tables.creation.success')
            logger.info("Database tables created successfully")
        except Exception as e:
            statsd_client.incr('application.database.tables.creation.error')
            logger.error(f"Failed to create database tables: {e}")
            exit(1)
    
    # Start the application
    statsd_client.incr('application.startup.success')
    app.run(host=os.getenv('HOSTNAME'))