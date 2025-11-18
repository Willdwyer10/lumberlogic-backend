# app/routes/optimizer_routes.py
from flask import Blueprint, request, jsonify
from app.optimizer.optimizer import optimize_boards
from app.middleware.auth_middleware import require_auth, optional_auth
from app.services.optimization_service import OptimizationService

bp = Blueprint('optimizer', __name__, url_prefix='/optimize')
optimization_service = OptimizationService()

@bp.route('', methods=['POST'])
@optional_auth  # Allow both authenticated and anonymous users
def optimize(current_user=None):
    """
    Optimize board cutting plan
    
    Accepts authenticated or anonymous requests.
    If authenticated, saves optimization to user's history.
    """
    try:
        data = request.get_json(force=True)
        cuts = data.get("cuts")
        boards = data.get("boards")
        project_name = data.get("project_name")  # Optional

        if not cuts or not boards:
            return jsonify({"error": "Both 'cuts' and 'boards' are required"}), 400

        # Run optimization
        result = optimize_boards(cuts, boards)
        
        # If user is authenticated, save to history
        if current_user:
            optimization_service.save_optimization(
                user_id=current_user['id'],
                cuts=cuts,
                boards=boards,
                result=result,
                project_name=project_name
            )
        
        return jsonify(result), 200

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@bp.route('/history', methods=['GET'])
@require_auth
def get_optimization_history(current_user):
    """Get user's optimization history"""
    try:
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        
        history = optimization_service.get_user_history(
            user_id=current_user['id'],
            page=page,
            limit=limit
        )
        
        return jsonify(history), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/history/<optimization_id>', methods=['GET'])
@require_auth
def get_optimization(current_user, optimization_id):
    """Get specific optimization by ID"""
    try:
        optimization = optimization_service.get_optimization(
            optimization_id=optimization_id,
            user_id=current_user['id']
        )
        
        if not optimization:
            return jsonify({"error": "Optimization not found"}), 404
        
        return jsonify(optimization), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/history/<optimization_id>', methods=['DELETE'])
@require_auth
def delete_optimization(current_user, optimization_id):
    """Delete optimization from history"""
    try:
        success = optimization_service.delete_optimization(
            optimization_id=optimization_id,
            user_id=current_user['id']
        )
        
        if not success:
            return jsonify({"error": "Optimization not found"}), 404
        
        return jsonify({"message": "Optimization deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500