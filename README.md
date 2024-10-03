# User Management API

## Overview

This API provides endpoints for managing user accounts, including creating, updating, and retrieving user information. It is built using Flask, with SQLAlchemy for database interactions and HTTP Basic Auth for authentication.

## Endpoints

### 1. Health Check

- **Endpoint:** `/healthz`
- **Method:** `GET`
- **Description:** Checks the health of the application by verifying the database connection.
- **Response:**
  - **200 OK:** The application is healthy.
  - **503 Service Unavailable:** The database connection failed.

### 2. Create User

- **Endpoint:** `/v1/user`
- **Method:** `POST`
- **Description:** Creates a new user with the provided information.
- **Request Body:**
  - **JSON:** `{"first_name": "string", "last_name": "string", "email": "string", "password": "string"}`
- **Response:**
  - **201 Created:** The user was created successfully.
  - **400 Bad Request:** Invalid request (e.g., missing required fields, invalid email or password).
  - **500 Internal Server Error:** An unexpected error occurred.

### 3. Update User

- **Endpoint:** `/v1/user/self`
- **Method:** `PUT`
- **Description:** Updates the current user's information.
- **Request Body:**
  - **JSON:** `{"first_name": "string", "last_name": "string", "password": "string"}`
- **Response:**
  - **200 OK:** The user was updated successfully.
  - **400 Bad Request:** Invalid request (e.g., invalid name or password).

### 4. Get User

- **Endpoint:** `/v1/user/self`
- **Method:** `GET`
- **Description:** Retrieves the current user's information.
- **Response:**
  - **200 OK:** The user's information was retrieved successfully.
  - **400 Bad Request:** Invalid request (e.g., request body was not empty).

## Authentication

The API uses HTTP Basic Auth for authentication. The `email` and `password` are used as the username and password for authentication.

## Requirements

The following Python packages are required:

- Flask
- Flask-SQLAlchemy
- Flask-HTTPAuth
- Werkzeug
- SQLAlchemy

## Setup Instructions

1. **Clone the Repository**

   ```bash
   git clone https://github.com/username/flask-user-management.git
   ```

2. **Navigate to the Repository Directory**

   ```bash
   cd flask-user-management
   ```

3. **Create a Virtual Environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. **Install Dependencies**

   Create a `requirements.txt` file with the following content:

   ```
   Flask>=2.0
   Flask-SQLAlchemy>=2.5
   Flask-HTTPAuth>=4.4
   Werkzeug>=2.0
   ```

   Then install the dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. **Set Environment Variables**

   Ensure you have set the necessary environment variables:

   ```bash
   export SQLALCHEMY_DATABASE_URI='your-database-uri'
   export HOSTNAME='0.0.0.0'
   ```

6. **Run the Application**

   ```bash
   python app.py
   ```

## Dependencies

The application depends on several Python libraries, which are listed in the `requirements.txt` file:

```plaintext
Flask>=2.0
Flask-SQLAlchemy>=2.5
Flask-HTTPAuth>=4.4
Werkzeug>=2.0
```

These dependencies can be installed using pip as described in the setup instructions above.

## Additional Notes

Ensure that your database is properly configured and accessible using the URI specified in `SQLALCHEMY_DATABASE_URI`. Adjust any configurations as needed for your specific environment or deployment scenario.