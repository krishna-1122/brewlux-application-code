"""Consistent JSON error response helpers."""
from flask import jsonify

def error_response(code, message, status):
    return jsonify({
        "error": {
            "code": code,
            "message": message,
        }
    }), status
