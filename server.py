import os

from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta
import logging
logging.basicConfig(level=logging.DEBUG)
import datetime
import mysql.connector
from redis import Redis
import random
import string


try:
    MYSQLREP_HOST_NAME = os.environ.get('MYSQLREP_HOST_NAME')
    MYSQLREP_PORT = os.environ.get('MYSQLREP_PORT')
    MYSQLREP_DATABASE = os.environ.get('MYSQLREP_DATABASE')
    MYSQLREP_USER = os.environ.get('MYSQLREP_USER')
    MYSQLREP_PASSWORD = os.environ.get('MYSQLREP_PASSWORD')
except Exception as e:
    print(f"cannot fetch MySQLREP DB details from environment {e}")

try:
    MYSQL_HOST_NAME = os.environ.get('MYSQL_HOST_NAME')
    MYSQL_PORT = os.environ.get('MYSQL_PORT')
    MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE')
    MYSQL_USER = os.environ.get('MYSQL_USER')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD')
except Exception as e:
    print(f"cannot fetch MySQL DB details from environment {e}")

try:
    REDIS_HOST_NAME = os.environ.get('REDIS_HOST_NAME')
    REDIS_PORT = os.environ.get('REDIS_PORT')
    REDIS_DATABASE = os.environ.get('REDIS_DATABASE')
    REDIS_PASSWORD = os.environ.get('REDIS_PASSWORD')
except Exception as e:
    print(f"cannot fetch REDIS details from environment {e}")

JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
JWT_ACCESS_TOKEN_EXPIRE_HOURS = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRE_HOURS'))

def databaseconn():
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST_NAME,
            port=MYSQL_PORT,
            database=MYSQL_DATABASE,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"An error occurred: {e}")


def repdatabaseconn():
    try:
        conn = mysql.connector.connect(
            host=MYSQLREP_HOST_NAME,
            port=MYSQLREP_PORT,
            database=MYSQLREP_DATABASE,
            user=MYSQLREP_USER,
            password=MYSQLREP_PASSWORD
        )
        return conn
    except Exception as e:
        print(f"An error occurred: {e}")
        
app = Flask(__name__)
ACCESS_EXPIRES = timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)

app.config['JWT_SECRET_KEY'] = JWT_SECRET_KEY
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = ACCESS_EXPIRES

redis_client = Redis(host=REDIS_HOST_NAME, port=REDIS_PORT, db=REDIS_DATABASE, password=REDIS_PASSWORD)
jwt = JWTManager(app)

def loyalty_card_id_gen(size=6):
    """Generate random 6 character alphanumeric string"""
    # List of characters [a-zA-Z0-9]
    chars = string.ascii_letters + string.digits
    code = "".join(random.choices(chars, k=6))
    return code

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    try:
        conn = databaseconn()
    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    if conn is not None:
        data = request.get_json()
        first_name = data.get('first_name') 
        last_name = data.get('last_name')
        password = data.get('password')
        email = data.get('email')
        created_at = data.get('created_at')
        # print(username,first_name,last_name,password,email)
        try:
            cursor = conn.cursor()
            # Check if the user already exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                # User already exists
                cursor.close()
                conn.close()
                return jsonify({"message": "User already exists"}), 409
            # User does not exist, proceed with signup
            password_hash = generate_password_hash(password)
            insert_query = """
                INSERT INTO users (first_name, last_name, password, email, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (first_name,last_name, password_hash, email, created_at))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            stored_userID = user[0]
            cursor.close()
            identities = {
                    "email": email,
                    "userID": stored_userID
                }
            # print(f"User '{username}' signed up successfully")
            conn.close()
            access_token = create_access_token(identity=identities)
            return jsonify({"message": "User signed up", "access_token": access_token}), 201
        except Exception as e:
            conn.rollback()
            print(f"Error: {e}")
            conn.close()
            return jsonify({"message": "Unable to sign up"}), 400

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        conn = databaseconn()
    except Exception as e:
        # print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    if conn is not None:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        try:
            cursor = conn.cursor()
            # Check if the user exists
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user:
                # Verify password
                stored_password_hash = user[4]  # Assuming password hash is stored in the third column
                stored_userID = user[0]
                identities = {
                    "email": email,
                    "userID": stored_userID
                }
                if check_password_hash(stored_password_hash, password):
                    # Passwords match, generate JWT token
                    access_token = create_access_token(identity=identities)
                    conn.close()
                    return jsonify({"message": "Login successful", "access_token": access_token}), 200
                else:
                    # Passwords don't match
                    conn.close()
                    return jsonify({"message": "Invalid email or password"}), 401
            else:
                # User not found
                conn.close()
                return jsonify({"message": "Invalid email or password"}), 401
        except Exception as e:
            # print(f"Error: {e}")
            conn.close()
            return jsonify({"message": "Unable to login"}), 500

@app.route('/api/auth/logout', methods=['DELETE'])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    # print(jti)
    redis_client.set(jti, "", ex=ACCESS_EXPIRES)
    return jsonify(msg="Access token revoked")

# Callback function to check if a JWT exists in the redis blocklist
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload: dict):
    jti = jwt_payload["jti"]
    token_in_redis = redis_client.get(jti)
    return token_in_redis is not None

@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    return jsonify(hello="world")

@app.route('/api/user/loyalty', methods=['POST'])
@jwt_required()
def user_loyalty_add():
    try:
        conn = databaseconn()
    except Exception as e:
        # print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    data = request.get_json()

    identities = get_jwt_identity()
    # Extract email and userID from the identities dictionary
    email = identities.get("email")
    try:
        cursor = conn.cursor()
        # Check if the user already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        loyalcard = cursor.fetchone()
        if loyalcard[6]:
            cursor.close()
            conn.close()
            return jsonify({"message": "Loyalty already exists", "loyalty_card_id": loyalcard[6]}), 409
        loyalty_card_id = loyalty_card_id_gen()
        insert_query = """
            INSERT INTO users (email, loyalty_card_id)
            VALUES (%s, %s)
        """
        cursor.execute(insert_query, (email,loyalty_card_id))
        conn.commit()
        cursor.close()
        return jsonify({"message": "loyalty card added", "loyalty_card_id": loyalty_card_id}), 200
    except Exception as e:
        print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to add to DB", "error": f"{e}"}), 500


@app.route("/api/user/profile", methods=["GET"])
@jwt_required()
def user_profile():
    identities = get_jwt_identity()

    # Extract email and userID from the identities dictionary
    email = identities.get("email")
    userID = identities.get("userID")
    try:
        conn = databaseconn()
    except Exception as e:
        # print(f"An error occurred: {e}")
        return jsonify({"message": "Database Down"}), 500
    try:
        cursor = conn.cursor()
        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_profile_details = cursor.fetchone()
        if user_profile_details:
            return jsonify({"first_name": user_profile_details[1], "last_name": user_profile_details[2], "email": user_profile_details[3], "created_at": user_profile_details[5], "loyalty_card_id": user_profile_details[6]}), 200
        else:
            # User not found
            conn.close()
            return jsonify({"message": "Invalid email or password"}), 401
    except Exception as e:
        # print(f"Error: {e}")
        conn.close()
        return jsonify({"message": "Unable to login"}), 500



if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port= 8080)  