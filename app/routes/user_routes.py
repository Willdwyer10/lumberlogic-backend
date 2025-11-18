# app/routes/user_routes.py
from flask import Blueprint, request, jsonify
from app.middleware.auth_middleware import require_auth
from app.services.user_service import UserService

bp = Blueprint('users', __name__, url_prefix='/users')
user_service = UserService()

@bp.route('/profile', methods=['GET'])
@require_auth
def get_profile(current_user):
    """Get user profile"""
    return jsonify({
        "id": current_user['id'],
        "email": current_user['email'],
        "name": current_user['name'],
        "picture": current_user.get('picture'),
        "created_at": current_user.get('created_at')
    }), 200


@bp.route('/profile', methods=['PUT'])
@require_auth
def update_profile(current_user):
    """Update user profile"""
    try:
        data = request.get_json()
        allowed_fields = ['name']  # Add more fields as needed
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not update_data:
            return jsonify({"error": "No valid fields to update"}), 400
        
        updated_user = user_service.update_user(current_user['id'], update_data)
        
        return jsonify(updated_user), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/account', methods=['DELETE'])
@require_auth
def delete_account(current_user):
    """Delete user account"""
    try:
        success = user_service.delete_user(current_user['id'])
        
        if not success:
            return jsonify({"error": "Failed to delete account"}), 500
        
        return jsonify({"message": "Account deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500