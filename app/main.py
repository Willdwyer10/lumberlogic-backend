from flask import Flask, request, jsonify
from optimizer.optimizer import optimize_boards

app = Flask(__name__)

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


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
