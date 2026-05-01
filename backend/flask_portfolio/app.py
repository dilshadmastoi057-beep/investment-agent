from flask import Flask, jsonify
from flask_cors import CORS

from portfolio_service import build_portfolio_snapshot


app = Flask(__name__)
CORS(app)


@app.get("/")
def home():
    return jsonify({"message": "Flask AI portfolio API is running."})


@app.get("/portfolio")
def portfolio():
    try:
        snapshot = build_portfolio_snapshot()
        return jsonify(snapshot)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
