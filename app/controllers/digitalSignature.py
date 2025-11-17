from flask import Blueprint, request, jsonify
import base64
import os
import datetime
from ..models.approval_model import Approval
from ..middleware.auth_middleware import token_required

digital_signature_bp = Blueprint('digital_signature', __name__, url_prefix='/api/signatures')

# Create uploads folder if not exist
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@digital_signature_bp.route('/upload', methods=['POST'])
@token_required
def upload_signature(current_user):
    """
    Upload and save digital signature
    """
    data = request.get_json()
    signature = data.get('signature')

    if not signature:
        return jsonify({"error": "No signature provided"}), 400

    try:
        # Extract base64 image content
        header, encoded = signature.split(",", 1)
        binary_data = base64.b64decode(encoded)

        # Save to file
        filename = f"signature_{current_user.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(file_path, "wb") as f:
            f.write(binary_data)

        return jsonify({
            "message": "Signature saved successfully",
            "path": f"/uploads/{filename}"
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@digital_signature_bp.route('/approval/<approval_id>', methods=['GET'])
@token_required
def get_approval_signature(current_user, approval_id):
    """
    Get signature for a specific approval
    """
    approval = Approval.objects(id=approval_id).first()
    if not approval or not approval.signature:
        return jsonify({"error": "Signature not found"}), 404
    
    # Verify the current user has access to this approval
    if str(approval.approver_id) != str(current_user.id) and current_user.role not in ['admin']:
        return jsonify({"error": "Unauthorized"}), 403
    
    return jsonify({
        "signature": approval.signature,
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else None
    }), 200