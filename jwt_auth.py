import os
from functools import wraps
from flask import request, jsonify, g
from jose import jwt, JWTError
from dotenv import load_dotenv


load_dotenv()

# Default secret key (for local/dev use)
DEFAULT_SECRET_KEY = "your_super_secret_jwt_key_here_make_it_long_and_secure_123456789"

# Load from environment, else use default
SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_SECRET_KEY)

print(f"✅ Using SECRET_KEY: {'from environment' if os.getenv('JWT_SECRET_KEY') else 'default value'}")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header[len("Bearer "):]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except JWTError:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Extract user info from token payload
        g.user_email = payload.get("email")
        g.user_name = payload.get("username") or payload.get("user_id")

        if not g.user_email:
            return jsonify({"error": "Email not found in token"}), 401

        return f(*args, **kwargs)

    return decorated
