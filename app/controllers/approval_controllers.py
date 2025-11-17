
# routes/approval_routes.py
from flask import Blueprint, request, jsonify
from bson import ObjectId
from ..models.notice_model import Notice, Approval
from ..models.user_model import User
from ..middleware.auth_middleware import token_required, role_required
from datetime import datetime
import base64
import os

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'uploads')
approval_bp = Blueprint('approvals', __name__, url_prefix='/api/approvals')

from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from ..models import Notice, Approval, User
from ..middleware.auth_middleware import token_required

approval_bp = Blueprint('approvals', __name__, url_prefix='/api/approvals')

@approval_bp.route('/notices/<notice_id>/request-approval', methods=['POST'])
@token_required
def request_approval(current_user, notice_id):
    try:
        # Verify notice exists
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        # Get all employees (excluding students)
        approvers = User.objects(role__ne="student").all()
        if not approvers:
            notice.update(status="published", approval_status="auto_approved")
            return jsonify({"message": "No approvers found, notice auto-approved"}), 200

        # Create approval records
        approvals = []
        for approver in approvers:
            approval = Approval(
                notice=notice,
                approver=approver,
                status="pending"
            ).save()
            approvals.append(str(approval.id))

        # Update notice status
        notice.update(
            approval_status="pending",
            status="pending_approval",
            approvals=approvals
        )

        return jsonify({
            "message": f"Approval requested from {len(approvers)} employees",
            "notice_id": str(notice.id)
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/notices/pending', methods=['GET'])
@token_required
def get_pending_approvals(current_user):
    try:
        # Get notices pending approval by current user
        pending_notices = Notice.objects(
            approval_status="pending",
            approval_workflow__approver_id=str(current_user.id),
            approval_workflow__status="pending"
        ).order_by('-created_at')
        
        notices_data = []
        for notice in pending_notices:
            # Find the specific approval record for this user
            approval = next(
                (a for a in notice.approval_workflow 
                 if a.approver_id == str(current_user.id) and a.status == "pending"),
                None
            )
            
            if approval:
                notices_data.append({
                    "notice_id": str(notice.id),
                    "title": notice.title,
                    "content": notice.content,
                    "requested_by": notice.created_by,
                    "requested_at": notice.created_at.isoformat(),
                    "approval_id": str(approval.id),
                    "approval_level": notice.current_approval_level + 1,
                    "total_approvers": len(notice.approval_workflow)
                })
        
        return jsonify(notices_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/<approval_id>/approve', methods=['POST'])
@token_required
def approve_notice(current_user, approval_id):
    try:
        approval = Approval.objects(id=ObjectId(approval_id)).first()
        if not approval:
            return jsonify({"error": "Approval record not found"}), 404
            
        if approval.approver_id != str(current_user.id):
            return jsonify({"error": "Unauthorized to approve this notice"}), 403
            
        if approval.status != "pending":
            return jsonify({"error": "Approval already processed"}), 400
            
        notice = Notice.objects(approval_workflow__contains=approval).first()
        if not notice:
            return jsonify({"error": "Associated notice not found"}), 404
            
        # Update approval record
        approval.update(
            status="approved",
            approved_at=datetime.datetime.now(),
            comments=request.json.get("comments", "")
        )
        
        # Check if this was the last approval needed
        if notice.current_approval_level == len(notice.approval_workflow) - 1:
            notice.update(
                approval_status="approved",
                status="published",
                publish_at=datetime.datetime.now()
            )
            # TODO: Send notification to creator and publish notice
        else:
            # Move to next approver
            notice.update(inc__current_approval_level=1)
            # TODO: Send notification to next approver
            
        return jsonify({
            "message": "Notice approved successfully",
            "notice_id": str(notice.id),
            "status": "approved"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/<approval_id>/reject', methods=['POST'])
@token_required
def reject_notice(current_user, approval_id):
    try:
        approval = Approval.objects(id=ObjectId(approval_id)).first()
        if not approval:
            return jsonify({"error": "Approval record not found"}), 404
            
        if approval.approver_id != str(current_user.id):
            return jsonify({"error": "Unauthorized to reject this notice"}), 403
            
        if approval.status != "pending":
            return jsonify({"error": "Approval already processed"}), 400
            
        notice = Notice.objects(approval_workflow__contains=approval).first()
        if not notice:
            return jsonify({"error": "Associated notice not found"}), 404
            
        # Update approval record
        rejection_reason = request.json.get("reason", "")
        approval.update(
            status="rejected",
            approved_at=datetime.datetime.now(),
            comments=rejection_reason
        )
        
        # Reject the notice
        notice.update(
            approval_status="rejected",
            status="rejected",
            rejection_reason=rejection_reason
        )
        
        # TODO: Send notification to creator
        
        return jsonify({
            "message": "Notice rejected",
            "notice_id": str(notice.id),
            "status": "rejected",
            "reason": rejection_reason
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
# routes/approval_routes.py
@approval_bp.route('/<approval_id>/sign', methods=['POST'])
@token_required
def sign_approval(current_user, approval_id):
    try:
        approval = Approval.objects(id=ObjectId(approval_id)).first()
        if not approval:
            return jsonify({"error": "Approval record not found"}), 404
            
        if approval.approver_id != str(current_user.id):
            return jsonify({"error": "Unauthorized to sign this approval"}), 403
            
        if approval.status != "approved":
            return jsonify({"error": "Approval must be approved before signing"}), 400
            
        signature_data = request.json.get("signature")
        if not signature_data:
            return jsonify({"error": "Signature data required"}), 400
            
        # Save signature image
        header, encoded = signature_data.split(",", 1)
        binary_data = base64.b64decode(encoded)
        
        filename = f"signature_{approval_id}.png"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        with open(filepath, "wb") as f:
            f.write(binary_data)
            
        approval.update(
            signature_image=filename,
            signed_at=datetime.datetime.now()
        )
        
        return jsonify({
            "message": "Approval signed successfully",
            "signature_path": f"/uploads/{filename}"
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_approvers_for_notice(notice):
    """
    Helper function to determine approval workflow based on notice attributes
    """
    # This should be customized based on your organizational structure
    # Example: Get department heads for the notice's department
    approvers = User.objects(
        role__in=["dean", "director"],
        department__in=notice.departments
    ).limit(2)  # Example: 2-level approval
    
    return list(approvers)