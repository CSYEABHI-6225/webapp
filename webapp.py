
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
from datetime import datetime 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from logging.handlers import RotatingFileHandler  # Add this import
import re
import os
import uuid
import logging
import boto3
from botocore.exceptions import ClientError
import watchtower
import logging.config
import statsd
import atexit

# Near the top of webapp.py, after your imports
USE_CLOUDWATCH = os.getenv('USE_CLOUDWATCH', 'false').lower() == 'true'

# Replace your CloudWatch configuration with this conditional block
if USE_CLOUDWATCH:
    cloudwatch_handler = watchtower.CloudWatchLogHandler(
        log_group_name=app.config['AWS_CLOUDWATCH_LOG_GROUP'],
        log_stream_name=app.config['AWS_CLOUDWATCH_LOG_STREAM'],
        use_queues=False,
        create_log_group=True
    )
    logger.addHandler(cloudwatch_handler)

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

load_dotenv()

app = Flask(__name__)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['HOSTNAME'] = os.getenv('HOSTNAME')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# AWS Configuration
# AWS Configuration
# AWS Configuration
app.config['AWS_ACCESS_KEY'] = os.getenv('AWS_ACCESS_KEY')
app.config['AWS_SECRET_KEY'] = os.getenv('AWS_SECRET_KEY')
app.config['AWS_BUCKET_NAME'] = os.getenv('AWS_BUCKET_NAME')
app.config['AWS_REGION'] = os.getenv('AWS_REGION')
app.config['AWS_CLOUDWATCH_LOG_GROUP'] = os.getenv('AWS_CLOUDWATCH_LOG_GROUP', '/csye6225/webapp')
app.config['AWS_CLOUDWATCH_LOG_STREAM'] = datetime.now().strftime('%Y/%m/%d')  # Fixed datetime

# Initialize AWS session
aws_session = boto3.Session(
    aws_access_key_id=app.config['AWS_ACCESS_KEY'],
    aws_secret_access_key=app.config['AWS_SECRET_KEY'],
    region_name=app.config['AWS_REGION']
)

# Initialize S3 client
s3_client = aws_session.client('s3')

# Configure CloudWatch logging
cloudwatch_handler = watchtower.CloudWatchLogHandler(
    log_group_name=app.config['AWS_CLOUDWATCH_LOG_GROUP'],
    log_stream_name=app.config['AWS_CLOUDWATCH_LOG_STREAM'],
    use_queues=False,
    create_log_group=True
)

# Configure StatsD for metrics
statsd_client = statsd.StatsClient('localhost', 8125)

# Update logging configuration
logger.addHandler(cloudwatch_handler)

db = SQLAlchemy(app)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
auth = HTTPBasicAuth()

# Request logging
@app.before_request
def log_request_info():
    logger.info(f"Request Method: {request.method}")
    logger.info(f"Request URL: {request.url}")
    logger.info(f"Request Headers: {dict(request.headers)}")

# Error handling
@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled Exception: {str(e)}")
    return '', 500


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(36), primary_key=True, default=str(uuid.uuid4()))
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    account_created = db.Column(db.DateTime, default=datetime.utcnow)  # Changed this line
    account_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # Changed this line
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
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # Changed this line
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
    if not email or not password:
        return None
    if not validate_email(email):
        return None
    user = User.query.filter_by(email=email).first()
    if user and user.check_password(password):
        return user
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

# Previous API Endpoints

@app.route('/healthz', methods=['GET'])
def health_check():
    logger.info("GET /healthz - Health check request received")
    
    if check_queryparam():
        return '', 404

    if request.data:
        return '', 400

    if check_db_connection():
        return '', 200
    else:
        return '', 503

@app.route('/v1/user', methods=['POST'])
def create_user():
    logger.info("POST /v1/user - Create user request received")
    try:
        if check_queryparam():
            return '', 404

        data = request.json
        if not data:
            return '', 400

        required_keys = ('first_name', 'last_name', 'email', 'password')
        if not all(key in data for key in required_keys):
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
        logger.error(f"Error creating user: {str(e)}")
        db.session.rollback()
        return '', 500

@app.route('/v1/user/self', methods=['PUT'])
@auth.login_required
def update_user():
    logger.info("PUT /v1/user/self - Update user request received")
    if check_queryparam():
        return '', 404

    user = auth.current_user()
    data = request.json

    if not data:
        return '', 400

    required_fields = ['first_name', 'last_name', 'password']
    if not all(field in data for field in required_fields):
        return '', 400

    if not validate_name(data['first_name']):
        return '', 400
    if not validate_name(data['last_name']):
        return '', 400
    if not validate_password(data['password']):
        return '', 400

    user.first_name = data['first_name']
    user.last_name = data['last_name']
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
    logger.info("GET /v1/user/self - Get user request received")
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

# New Image Handling Endpoints
@app.route('/v1/user/self/pic', methods=['POST'])
@auth.login_required
def upload_profile_pic():
    start_time = datetime.now()
    logger.info("POST /v1/user/self/pic - Upload profile picture request received")
    
    # Record API call metric
    statsd_client.incr('api.upload_profile_pic.calls')
    
    if check_queryparam():
        logger.warning("Query parameters not allowed")
        statsd_client.incr('api.upload_profile_pic.errors')
        return '', 404

    if 'profilePic' not in request.files:
        logger.error("No profilePic part in request")
        statsd_client.incr('api.upload_profile_pic.errors')
        return '', 400

    file = request.files['profilePic']
    
    if file.filename == '':
        logger.error("No selected file")
        statsd_client.incr('api.upload_profile_pic.errors')
        return '', 400

    if not allowed_file(file.filename):
        logger.error(f"Invalid file type: {file.filename}")
        statsd_client.incr('api.upload_profile_pic.errors')
        return '', 400

    try:
        # Delete existing image from S3 and database if exists
        existing_image = Image.query.filter_by(user_id=auth.current_user().id).first()
        if existing_image:
            try:
                # Delete from S3
                file_extension = existing_image.file_name.rsplit('.', 1)[1].lower()
                s3_client.delete_object(
                    Bucket=app.config['AWS_BUCKET_NAME'],
                    Key=f"{auth.current_user().id}/profile.{file_extension}"
                )
            except ClientError as e:
                logger.error(f"Error deleting existing S3 object: {str(e)}")
                statsd_client.incr('api.s3.delete.errors')
            
            db.session.delete(existing_image)
            db.session.commit()

        # Get current user's ID and prepare file
        user_id = auth.current_user().id
        original_filename = secure_filename(file.filename)
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        s3_key = f"{user_id}/profile.{file_extension}"

        # Upload to S3
        upload_start_time = datetime.now()
        try:
            s3_client.upload_fileobj(
                file,
                app.config['AWS_BUCKET_NAME'],
                s3_key,
                ExtraArgs={
                    'ContentType': f'image/{file_extension}',
                    'ACL': 'private'
                }
            )
            # Record S3 upload latency
            upload_duration = (datetime.now() - upload_start_time).total_seconds() * 1000
            statsd_client.timing('api.s3.upload.latency', upload_duration)
            statsd_client.incr('api.s3.upload.success')
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            statsd_client.incr('api.s3.upload.errors')
            return '', 500

        # Create database record
        image = Image(
            id=user_id,
            file_name=original_filename,
            url=f"{app.config['AWS_BUCKET_NAME']}/{s3_key}",
            user_id=user_id
        )
        
        db.session.add(image)
        db.session.commit()

        # Record total latency
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() * 1000
        statsd_client.timing('api.upload_profile_pic.latency', duration)
        
        # Record success metric
        statsd_client.incr('api.upload_profile_pic.success')

        return jsonify({
            "file_name": image.file_name,
            "id": image.id,
            "url": image.url,
            "upload_date": image.upload_date.strftime("%Y-%m-%d"),
            "user_id": image.user_id
        }), 201

    except Exception as e:
        # Record error metrics
        statsd_client.incr('api.upload_profile_pic.errors')
        logger.error(f"Error uploading profile picture: {str(e)}")
        db.session.rollback()
        return '', 500

@app.route('/v1/user/self/pic', methods=['GET'])
@auth.login_required
def get_profile_pic():
    logger.info("GET /v1/user/self/pic - Get profile picture request received")
    
    if check_queryparam():
        return '', 404

    if request.data:
        return '', 400

    try:
        image = Image.query.filter_by(user_id=auth.current_user().id).first()
        if not image:
            return '', 404

        return jsonify({
            "file_name": image.file_name,
            "id": image.id,
            "url": image.url,
            "upload_date": image.upload_date.strftime("%Y-%m-%d"),
            "user_id": image.user_id
        }), 200

    except Exception as e:
        logger.error(f"Error retrieving profile picture: {str(e)}")
        return '', 500

@app.route('/v1/user/self/pic', methods=['DELETE'])
@auth.login_required
def delete_profile_pic():
    logger.info("DELETE /v1/user/self/pic - Delete profile picture request received")
    
    if check_queryparam():
        return '', 404

    try:
        image = Image.query.filter_by(user_id=auth.current_user().id).first()
        if not image:
            return '', 404

        # Delete from S3
        try:
            file_extension = image.file_name.rsplit('.', 1)[1].lower()
            s3_key = f"{auth.current_user().id}/profile.{file_extension}"
            s3_client.delete_object(
                Bucket=app.config['AWS_BUCKET_NAME'],
                Key=s3_key
            )
        except ClientError as e:
            logger.error(f"Error deleting from S3: {str(e)}")

        # Delete from database
        db.session.delete(image)
        db.session.commit()

        return '', 204

    except Exception as e:
        logger.error(f"Error deleting profile picture: {str(e)}")
        db.session.rollback()
        return '', 500

@app.errorhandler(405)
def method_not_allowed(e):
    logger.warning(f"Method not allowed: {request.method} {request.path}")
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
    statsd_client.incr('api.errors')
    return '', 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host=os.getenv('HOSTNAME'))