# app/middleware/auth_middleware.py
from functools import wraps
from flask import request, jsonify
from app.services.auth_service import AuthService

auth_service = AuthService()

def require_auth(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({"error": "Authentication required"}), 401
        
        # Verify token
        current_user = auth_service.verify_access_token(token)
        
        if not current_user:
            return jsonify({"error": "Invalid or expired token"}), 401
        
        # Pass user to the route function
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """Decorator for endpoints that work with or without authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_user = None
        
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            current_user = auth_service.verify_access_token(token)
        
        # Pass user (or None) to the route function
        return f(current_user=current_user, *args, **kwargs)
    
    return decorated_function