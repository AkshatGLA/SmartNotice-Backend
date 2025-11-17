from flask import jsonify
from ..models.user_model import User
from ..middleware.auth_middleware import token_required

def init_user_routes(app):
    @app.route("/api/users", methods=["GET"])
    @token_required
    def get_users(current_user):
        try:
            users = User.objects().only('id', 'name', 'email')
            return jsonify([{
                "id": str(user.id),
                "name": user.name,
                "email": user.email
            } for user in users]), 200
        except Exception as e:
            print(f"Users error: {str(e)}")
            return jsonify({"error": "Failed to fetch users"}), 500