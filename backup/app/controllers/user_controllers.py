from flask import Blueprint, jsonify
from ..models.user_model import User
from ..middleware.auth_middleware import token_required, role_required
from ..models.student_model import Student

user_bp = Blueprint('users', __name__, url_prefix='/api/users')

@user_bp.route("", methods=["GET"])
@token_required
# @role_required(['admin'])
def get_users(current_user):
    try:
        users = User.objects().only('id', 'name', 'email')
        return jsonify([{
            "id": str(user.id),
            "name": user.name,
            "email": user.email
        } for user in users]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@user_bp.route("/count", methods=["GET"])
@token_required
# @role_required(['admin'])
def get_users_count(current_user):
    try:
        count = Student.objects.count()
        return jsonify({"count": count}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500