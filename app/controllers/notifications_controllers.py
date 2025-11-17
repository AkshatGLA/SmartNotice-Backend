from flask import Blueprint, jsonify, request
from ..models.notifications_model import Notification
from ..middleware.auth_middleware import token_required

notification_bp = Blueprint('notifications', __name__, url_prefix='/api/notifications')

@notification_bp.route('', methods=['GET'])
@token_required
def get_notifications(current_user):
    try:
        notifications = Notification.objects(user_id=str(current_user.id))\
            .order_by('-created_at')\
            .limit(20)
        return jsonify([n.to_dict() for n in notifications]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notification_bp.route('/<notification_id>/read', methods=['PUT'])
@token_required
def mark_as_read(current_user, notification_id):
    try:
        notification = Notification.objects(
            id=notification_id,
            user_id=str(current_user.id)
        ).first()
        if not notification:
            return jsonify({"error": "Notification not found"}), 404
            
        notification.update(is_read=True)
        return jsonify(notification.to_dict()), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notification_bp.route('/read-all', methods=['PUT'])
@token_required
def mark_all_as_read(current_user):
    try:
        Notification.objects(
            user_id=str(current_user.id),
            is_read=False
        ).update(is_read=True)
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500