# app/routes/auth_routes.py
from flask import Blueprint, request, jsonify, redirect, session, url_for
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import require_auth
import os

bp = Blueprint('auth', __name__, url_prefix='/auth')
auth_service = AuthService()

@bp.route('/google/login', methods=['GET'])
def google_login():
    """Initiate Google OAuth flow"""
    try:
        authorization_url = auth_service.get_google_authorization_url()
        return jsonify({"authorization_url": authorization_url}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/google/callback', methods=['GET'])
def google_callback():
    """Handle Google OAuth callback"""
    try:
        code = request.args.get('code')
        if not code:
            return jsonify({"error": "No authorization code provided"}), 400
        
        # Exchange code for tokens and get user info
        result = auth_service.handle_google_callback(code)
        
        if not result:
            return jsonify({"error": "Authentication failed"}), 401
        
        # Redirect to frontend with tokens
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
        redirect_url = f"{frontend_url}/auth/callback?access_token={result['access_token']}&refresh_token={result['refresh_token']}"
        
        return redirect(redirect_url)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({"error": "Refresh token required"}), 400
        
        result = auth_service.refresh_access_token(refresh_token)
        
        if not result:
            return jsonify({"error": "Invalid refresh token"}), 401
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/logout', methods=['POST'])
@require_auth
def logout(current_user):
    """Logout user (client-side should delete tokens)"""
    # In a more complex system, you might invalidate tokens in a blacklist
    return jsonify({"message": "Logged out successfully"}), 200


@bp.route('/me', methods=['GET'])
@require_auth
def get_current_user(current_user):
    """Get current user information"""
    return jsonify({
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "picture": current_user.get('picture'),
        "created_at": current_user.get('created_at')
    }), 200