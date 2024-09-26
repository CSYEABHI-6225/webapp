# Flask Health Check Application

This is a simple Flask application that provides a health check endpoint to monitor the status of a MySQL database connection. It includes features to manage database connectivity and validates requests.

## Features

- **Health Check Endpoint**: 
  - `/healthz` (GET): Checks the database connection and returns HTTP status codes based on the connection status and request validity.
  
- **Query Parameter Check**: 
  - Returns `404 Not Found` if query parameters are included in the request.

- **Payload Validation**: 
  - Returns `400 Bad Request` if any payload is included in the request.

- **Cache Control**: 
  - The response is marked as `no-cache` to prevent caching.

- **Database Connection Management**: 
  - Singleton pattern ensures a single instance of the database connection.
  
- **Kill Database Connection**: 
  - `/kill-db` (POST): Kills the active database connection, useful for testing failure scenarios.

## Requirements

- Python 3.6 or higher
- Flask
- Flask-SQLAlchemy
- MySQL database server

## Setup Instructions

1. **Clone the Repository**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
