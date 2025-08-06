from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from database import User
import jwt
from datetime import datetime, timedelta
import os

bcrypt = Bcrypt()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def hash_password(password):
    """Hash a password for storing in the database."""
    return bcrypt.generate_password_hash(password).decode('utf-8')

def check_password(password_hash, password):
    """Check if password matches the hash."""
    return bcrypt.check_password_hash(password_hash, password)

def generate_token(user_id):
    """Generate JWT token for API access."""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(days=1)
    }
    return jwt.encode(payload, os.getenv('SECRET_KEY'), algorithm='HS256')

def verify_token(token):
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
