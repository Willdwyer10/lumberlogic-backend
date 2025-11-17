from flask import Flask, request, jsonify
from flask_cors import CORS
from app.optimizer.optimizer import optimize_boards
from app.database.supabase_client import supabase

app = Flask(__name__)
CORS(app)

# ==========================
# Optimize endpoint
# ==========================
@app.route("/optimize", methods=["POST"])
def optimize():
    try:
        data = request.get_json(force=True)
        cuts = data.get("cuts")
        boards = data.get("boards")

        if not cuts or not boards:
            return jsonify({"error": "Both 'cuts' and 'boards' are required"}), 400

        result = optimize_boards(cuts, boards)
        return jsonify(result), 200

    except RuntimeError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500

# ==========================
# Health check endpoint
# ==========================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ==========================
# Users endpoints
# ==========================
@app.route("/users", methods=["POST"])
def add_user():
    data = request.get_json(force=True)
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not name or not email or not password:
        return jsonify({"error": "name, email, and password are required"}), 400

    try:
        response = supabase.table("users").insert({
            "name": name,
            "email": email,
            "password": password
        }).execute()

        # Check if response.data exists
        if response.data is None:
            return jsonify({"error": "Failed to insert user"}), 400

        return jsonify({"message": "User added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/users", methods=["GET"])
def list_users():
    try:
        response = supabase.table("users").select("name,email").execute()
        # If data is None, Supabase likely failed
        if response.data is None:
            return jsonify({"error": "Failed to fetch users"}), 400

        return jsonify(response.data), 200
    except Exception as e:
        # Catch unexpected errors (e.g., network issues)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
