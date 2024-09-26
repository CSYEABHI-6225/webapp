from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os

app = Flask(__name__)
print(os.getenv('SQLALCHEMY_DATABASE_URI'))
# Configure the database connection using SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# Singleton Database Connection Class
class DatabaseConnection:

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance.db = SQLAlchemy(app)
        return cls._instance

    def kill_connection(self):
        """Method to simulate killing the database connection."""
        # Close the session to kill the connection
        if self.db.session:
            self.db.session.remove()
            print("Database connection killed.")


db_connection = DatabaseConnection()


def check_queryparam() -> bool:
    return bool(request.args)


def check_db_connection() -> bool:
    """Check if the application can connect to the database."""
    try:
        # Execute a simple query to check the connection
        db_connection.db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(e)
        return False


@app.route('/healthz', methods=['GET'])
def health_check():
# Check if there are any query parameters

    if check_queryparam():
        return 'Query parameters not supported', 404

    # Check if there is a payload
    if request.data:
        return '', 400  # Bad Request

    # Check the database connection
    if check_db_connection():
        return '', 200  # OK if successful
    else:
        return '', 503  # Service Unavailable if connection fails


# @app.route('/kill-db', methods=['POST'])
# def kill_db():
#     """Endpoint to kill the database connection."""
#     db_connection.kill_connection()
#     return 'Database connection killed', 200

# Add the cache-control header to the response
@app.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-cache'
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
