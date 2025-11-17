# from flask import Blueprint, request, jsonify
# from bson import ObjectId
# from datetime import datetime, timedelta
# from ..models.notice_model import Notice
# from ..models.approval_model import Approval
# from ..models.employee_model import Employee
# from ..middleware.auth_middleware import token_required
# from ..utils.email_send_function import send_bulk_email
# import traceback
# import random
# import string
# from ..extensions import socketio  # Import socketio from extensions

# otp_store = {}  # In-memory store for OTPs; in production, use a persistent store like Redis

# approval_bp = Blueprint('approvals', __name__, url_prefix='/api/approvals')

# def emit_approval_update(notice_id, approval_data):
#     """Emit socket event for approval updates"""
#     socketio.emit('approval_update', {
#         'notice_id': notice_id,
#         'approval': approval_data
#     }, room=f'notice_{notice_id}')

# def emit_notice_status_update(notice_id, status_data):
#     """Emit socket event for notice status updates"""
#     socketio.emit('notice_status_update', {
#         'notice_id': notice_id,
#         'status': status_data
#     }, room=f'notice_{notice_id}')

# @approval_bp.route('/request', methods=['POST'])
# @token_required
# def request_approval(current_user):
#     try:
#         data = request.get_json()
#         notice_id = data.get('notice_id')
        
#         if not notice_id:
#             return jsonify({"error": "Notice ID is required"}), 400
            
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
        
#         # Check if notice already has an approval workflow
#         if notice.approval_workflow and len(notice.approval_workflow) > 0:
#             return jsonify({
#                 "success": False,
#                 "error": "Approval already requested for this notice",
#                 "notice_id": str(notice.id),
#                 "redirect_url": f"/approval-tracking/{str(notice.id)}"
#             }), 400
        
#         # Get ALL employees (excluding students) as approvers
#         approvers = Employee.objects(role__ne="student").all()
        
#         if not approvers:
#             # Auto-approve if no approvers found
#             notice.update(
#                 approval_status="approved",
#                 status="published",
#                 requires_approval=False,
#                 approved_by=str(current_user.id),
#                 approved_by_name=current_user.name,
#                 approved_at=datetime.utcnow(),
#                 approval_comments="Auto-approved (no approvers found)"
#             )
            
#             # Emit notice status update
#             emit_notice_status_update(str(notice.id), {
#                 'approval_status': 'approved',
#                 'status': 'published',
#                 'updated_at': datetime.utcnow().isoformat()
#             })
            
#             return jsonify({
#                 "success": True,
#                 "message": "No approvers found, notice approved automatically",
#                 "notice_id": str(notice.id),
#                 "auto_approved": True,
#                 "redirect_url": f"/notices"  # Redirect to notices list since it's auto-approved
#             }), 200
            
#         # Create approval records for each approver
#         approval_ids = []
#         for approver in approvers:
#             approval = Approval(
#                 notice_id=notice,  # Pass the Notice object
#                 approver_id=str(approver.id),
#                 approver_name=approver.name,
#                 approver_role=approver.role,
#                 approver_department=approver.department,
#                 status="pending"
#             ).save()
#             approval_ids.append(str(approval.id))
            
#         # Update the notice with approval workflow
#         notice.update(
#             set__approval_workflow=approval_ids,
#             set__approval_status="pending",
#             set__status="pending_approval"
#         )
        
#         # Emit notice status update
#         emit_notice_status_update(str(notice.id), {
#             'approval_status': 'pending',
#             'status': 'pending_approval',
#             'updated_at': datetime.utcnow().isoformat()
#         })
        
#         return jsonify({
#             "success": True,
#             "message": f"Approval request sent to {len(approvers)} employees.",
#             "notice_id": str(notice.id),
#             "approvers_count": len(approvers),
#             "approval_ids": approval_ids,
#             "redirect_url": f"/approval-tracking/{str(notice.id)}"  # Add redirect URL
#         }), 200
        
#     except Exception as e:
#         print(f"Error in request_approval: {str(e)}")
#         traceback.print_exc()
#         return jsonify({
#             "success": False,
#             "error": str(e),
#             "message": "Failed to request approval"
#         }), 500

# @approval_bp.route('/my', methods=['GET'])
# @token_required
# def get_my_approvals(current_user):
#     try:
#         print(f"Fetching approvals for user: {current_user.id}, {current_user.name}")
        
#         # Get approvals for the current user
#         approvals = Approval.objects(approver_id=str(current_user.id)).order_by('-created_at')
        
#         print(f"Found {approvals.count()} approvals in database")
        
#         # Prepare response data
#         approvals_data = []
#         for approval in approvals:
#             print(f"Processing approval: {approval.id}, status: {approval.status}")
            
#             # Get the associated notice - With ReferenceField, notice_id is the Notice object
#             try:
#                 notice = approval.notice_id
#                 if not notice:
#                     print(f"Notice not found for approval {approval.id}")
#                     continue
                    
#                 print(f"Found notice: {notice.title}")
                
#                 approval_data = {
#                     "_id": str(approval.id),
#                     "notice_id": str(notice.id),
#                     "status": approval.status,
#                     "comments": approval.comments,
#                     "createdAt": approval.created_at.isoformat(),
#                     "approvedAt": approval.approved_at.isoformat() if approval.approved_at else None,
#                     "approver_name": approval.approver_name,
#                     "approver_role": approval.approver_role,
#                     "approved_by_name": approval.approved_by_name,
#                     "notice": {
#                         "_id": str(notice.id),
#                         "title": notice.title,
#                         "content": notice.content,
#                         "notice_type": notice.notice_type,
#                         "attachments": notice.attachments or [],
#                         "created_at": notice.created_at.isoformat() if notice.created_at else None,
#                         "approval_status": notice.approval_status
#                     }
#                 }
                
#                 approvals_data.append(approval_data)
#                 print(f"Added approval to response: {approval.id}")
                
#             except Exception as e:
#                 print(f"Error processing approval {approval.id}: {str(e)}")
#                 continue
                
#         print(f"Returning {len(approvals_data)} approvals in response")
        
#         return jsonify({
#             "success": True,
#             "approvals": approvals_data,
#             "count": len(approvals_data)
#         }), 200
        
#     except Exception as e:
#         print(f"Error in get_my_approvals: {str(e)}")
#         return jsonify({
#             "success": False,
#             "error": "Failed to fetch approvals",
#             "approvals": [],
#             "count": 0
#         }), 500

# @approval_bp.route('/<approval_id>/approve', methods=['POST'])
# @token_required
# def approve_notice(current_user, approval_id):
#     try:
#         # Check if OTP verification is required
#         data = request.get_json()
#         otp = data.get("otp")
#         comments = data.get("comments", "")
        
#         # If OTP is provided, verify it first
#         if otp:
#             # Verify OTP before proceeding with approval
#             if approval_id not in otp_store:
#                 return jsonify({"error": "OTP not found or expired. Please request a new OTP."}), 400
                
#             stored_otp_data = otp_store[approval_id]
            
#             # Check expiration
#             if datetime.utcnow() > stored_otp_data['expires_at']:
#                 del otp_store[approval_id]
#                 return jsonify({"error": "OTP expired. Please request a new OTP."}), 400
                
#             # Verify OTP matches
#             if stored_otp_data['otp'] != otp:
#                 return jsonify({"error": "Invalid OTP. Please try again."}), 400
                
#             # OTP is valid - remove it from store
#             del otp_store[approval_id]
        
#         approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
#         if not approval:
#             return jsonify({"error": "Approval not found"}), 404
            
#         if approval.status != "pending":
#             return jsonify({"error": "Approval already processed"}), 400
        
#         # Update approval record
#         approval.update(
#             status="approved",
#             approved_at=datetime.utcnow(),
#             comments=comments,
#             approved_by_name=current_user.name,
#             approved_by_role=current_user.role
#         )
        
#         # Get the notice and approve it immediately
#         notice = approval.notice_id
#         if notice:
#             notice.update(
#                 approval_status="approved",
#                 status="published",
#                 approved_by=str(current_user.id),
#                 approved_by_name=current_user.name,
#                 approved_at=datetime.utcnow(),
#                 approval_comments=f"Approved by {current_user.name} ({current_user.role})"
#             )
            
#             # Emit approval update
#             emit_approval_update(str(notice.id), {
#                 'approval_id': approval_id,
#                 'status': 'approved',
#                 'approver_name': current_user.name,
#                 'approved_at': datetime.utcnow().isoformat(),
#                 'comments': comments
#             })
            
#             # Emit notice status update
#             emit_notice_status_update(str(notice.id), {
#                 'approval_status': 'approved',
#                 'status': 'published',
#                 'updated_at': datetime.utcnow().isoformat()
#             })
                
#         return jsonify({
#             "message": "Notice approved successfully",
#             "approved_by": current_user.name,
#             "approved_at": datetime.utcnow().isoformat()
#         }), 200
        
#     except Exception as e:
#         print(f"Error in approve_notice: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @approval_bp.route('/<approval_id>/reject', methods=['POST'])
# @token_required
# def reject_notice(current_user, approval_id):
#     try:
#         approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
#         if not approval:
#             return jsonify({"error": "Approval not found"}), 404
            
#         if approval.status != "pending":
#             return jsonify({"error": "Approval already processed"}), 400
            
#         data = request.get_json()
#         reason = data.get("reason", "")
#         if not reason:
#             return jsonify({"error": "Reason is required for rejection"}), 400
            
#         approval.update(
#             status="rejected",
#             approved_at=datetime.utcnow(),
#             comments=reason,
#             approved_by_name=current_user.name,
#             approved_by_role=current_user.role
#         )
        
#         # Immediately reject the notice
#         notice = approval.notice_id
#         if notice:
#             notice.update(
#                 approval_status="rejected",
#                 status="rejected",
#                 approved_by=str(current_user.id),
#                 approved_by_name=current_user.name,
#                 approved_at=datetime.utcnow(),
#                 rejection_reason=reason
#             )
            
#             # Emit approval update
#             emit_approval_update(str(notice.id), {
#                 'approval_id': approval_id,
#                 'status': 'rejected',
#                 'approver_name': current_user.name,
#                 'approved_at': datetime.utcnow().isoformat(),
#                 'comments': reason
#             })
            
#             # Emit notice status update
#             emit_notice_status_update(str(notice.id), {
#                 'approval_status': 'rejected',
#                 'status': 'rejected',
#                 'updated_at': datetime.utcnow().isoformat()
#             })
        
#         return jsonify({"message": "Notice rejected"}), 200
#     except Exception as e:
#         print(f"Error in reject_notice: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @approval_bp.route('/<approval_id>/sign', methods=['POST'])
# @token_required
# def sign_approval(current_user, approval_id):
#     try:
#         approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
#         if not approval:
#             return jsonify({"error": "Approval not found"}), 404
            
#         if approval.status != "pending":
#             return jsonify({"error": "Approval must be pending to sign"}), 400
            
#         data = request.get_json()
#         signature_data = data.get("signature")
#         if not signature_data:
#             return jsonify({"error": "Signature data is required"}), 400
            
#         comments = data.get("comments", "")
            
#         # Save signature and approve
#         approval.update(
#             signature=signature_data,
#             status="approved",
#             approved_at=datetime.utcnow(),
#             comments=comments,
#             approved_by_name=current_user.name,
#             approved_by_role=current_user.role
#         )
        
#         # Get the notice and approve it immediately
#         notice = approval.notice_id
#         if notice:
#             # Update notice status immediately
#             notice.update(
#                 approval_status="approved",
#                 status="published",
#                 approved_by=str(current_user.id),
#                 approved_by_name=current_user.name,
#                 approved_at=datetime.utcnow(),
#                 approval_comments=f"Signed and approved by {current_user.name} ({current_user.role})"
#             )
            
#             # Emit approval update
#             emit_approval_update(str(notice.id), {
#                 'approval_id': approval_id,
#                 'status': 'approved',
#                 'approver_name': current_user.name,
#                 'approved_at': datetime.utcnow().isoformat(),
#                 'comments': comments,
#                 'signed': True
#             })
            
#             # Emit notice status update
#             emit_notice_status_update(str(notice.id), {
#                 'approval_status': 'approved',
#                 'status': 'published',
#                 'updated_at': datetime.utcnow().isoformat()
#             })
                
#         return jsonify({
#             "message": "Approval signed successfully",
#             "approved_by": current_user.name
#         }), 200
        
#     except Exception as e:
#         print(f"Error in sign_approval: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# @approval_bp.route('/track/<notice_id>', methods=['GET'])
# @token_required
# def get_approval_tracking(current_user, notice_id):
#     """
#     Get approval tracking information for a specific notice
#     """
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
            
#         # Check if user has permission to view this notice
#         if str(current_user.id) != notice.created_by and current_user.role not in ['admin', 'academic_head']:
#             return jsonify({"error": "Unauthorized"}), 403
        
#         # Get all approval records for this notice
#         approvals = []
#         if hasattr(notice, 'approval_workflow') and notice.approval_workflow:
#             for approval_id in notice.approval_workflow:
#                 try:
#                     # Make sure we're converting string ID to ObjectId if needed
#                     if isinstance(approval_id, str):
#                         approval_id = ObjectId(approval_id)
                    
#                     approval = Approval.objects(id=approval_id).first()
#                     if approval:
#                         approvals.append({
#                             "id": str(approval.id),
#                             "approver_name": approval.approver_name,
#                             "approver_role": approval.approver_role,
#                             "approver_department": approval.approver_department,
#                             "status": approval.status,
#                             "comments": approval.comments,
#                             "created_at": approval.created_at.isoformat() if approval.created_at else None,
#                             "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
#                             "signature": approval.signature
#                         })
#                 except Exception as e:
#                     print(f"Error loading approval {approval_id}: {str(e)}")
#                     continue
        
#         # Get auto_publish_after_approval setting (with fallback)
#         auto_publish = getattr(notice, 'auto_publish_after_approval', False)
        
#         # Get approval_status (with fallback)
#         approval_status = getattr(notice, 'approval_status', 'not_required')
        
#         # Get created_by_name (with fallback)
#         created_by_name = getattr(notice, 'created_by_name', 'Unknown')
        
#         # Get created_by employee details (since employees create notices)
#         try:
#             created_by_employee = Employee.objects(id=ObjectId(notice.created_by)).first()
#             if created_by_employee:
#                 created_by_name = getattr(created_by_employee, 'name', created_by_name)
#         except:
#             # If not found as employee, try as user (fallback)
#             try:
#                 created_by_user = Employee.objects(id=ObjectId(notice.created_by)).first()
#                 if created_by_user:
#                     created_by_name = getattr(created_by_user, 'name', created_by_name)
#             except:
#                 pass  # Keep the default 'Unknown'
        
#         # Get notice title with fallback
#         notice_title = getattr(notice, 'title', 'Untitled Notice')
        
#         # Get created_at with fallback
#         created_at = getattr(notice, 'created_at', datetime.utcnow())
        
#         # Get requires_approval with fallback
#         requires_approval = getattr(notice, 'requires_approval', False)
        
#         return jsonify({
#             "success": True,
#             "notice_id": str(notice.id),
#             "notice_title": notice_title,
#             "auto_publish_after_approval": auto_publish,
#             "current_status": approval_status,
#             "approvals": approvals,
#             "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else datetime.utcnow().isoformat(),
#             "created_by": created_by_name,
#             "requires_approval": requires_approval
#         }), 200
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({
#             "success": False,
#             "error": str(e),
#             "message": "Failed to fetch approval tracking data"
#         }), 500

# @approval_bp.route('/track/<notice_id>/settings', methods=['PUT'])
# @token_required
# def update_approval_settings(current_user, notice_id):
#     """
#     Update approval settings for a notice
#     """
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
            
#         # Check if user has permission to modify this notice
#         if str(current_user.id) != notice.created_by:
#             return jsonify({"error": "Unauthorized"}), 403
            
#         data = request.json
#         auto_publish = data.get('auto_publish_after_approval', False)
        
#         notice.update(auto_publish_after_approval=auto_publish)
        
#         return jsonify({
#             "message": "Settings updated successfully",
#             "auto_publish_after_approval": auto_publish
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @approval_bp.route('/track/<notice_id>/publish', methods=['POST'])
# @token_required
# def manually_publish_notice(current_user, notice_id):
#     """
#     Manually publish a notice after approval
#     """
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
            
#         # Check if user has permission to publish this notice
#         if str(current_user.id) != notice.created_by:
#             return jsonify({"error": "Unauthorized"}), 403
            
#         # Check if notice is approved
#         if notice.approval_status != 'approved':
#             return jsonify({"error": "Notice must be approved before publishing"}), 400
            
#         # Check if notice is already published
#         if notice.status == 'published':
#             return jsonify({"error": "Notice is already published"}), 400
            
#         # Publish the notice
#         notice.update(
#             status='published',
#             publish_at=datetime.utcnow()
#         )
        
#         # Emit notice status update
#         emit_notice_status_update(str(notice.id), {
#             'status': 'published',
#             'publish_at': datetime.utcnow().isoformat(),
#             'updated_at': datetime.utcnow().isoformat()
#         })
        
#         return jsonify({
#             "message": "Notice published successfully",
#             "published_at": datetime.utcnow().isoformat()
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @approval_bp.route('/send-otp', methods=['POST'])
# @token_required
# def send_approval_otp(current_user):
#     try:
#         data = request.get_json()
#         approval_id = data.get('approval_id')
        
#         if not approval_id:
#             return jsonify({"error": "Approval ID is required"}), 400
            
#         # Use the current user's email from the token
#         approver_email = current_user.email  # or current_user.official_email
        
#         # Generate 6-digit OTP
#         otp = ''.join(random.choices(string.digits, k=6))
        
#         # Store OTP with expiration (5 minutes)
#         otp_store[approval_id] = {
#             'otp': otp,
#             'expires_at': datetime.utcnow() + timedelta(minutes=5),
#             'email': approver_email
#         }
        
#         # Send email with OTP
#         send_otp_email(approver_email, otp, approval_id)
        
#         return jsonify({
#             "message": "OTP sent successfully to your email",
#             "expires_in": 300  # 5 minutes in seconds
#         }), 200
        
#     except Exception as e:
#         print(f"Error sending OTP: {str(e)}")
#         return jsonify({"error": "Failed to send OTP"}), 500

# @approval_bp.route('/verify-otp', methods=['POST'])
# @token_required
# def verify_approval_otp(current_user):
#     try:
#         data = request.get_json()
#         approval_id = data.get('approval_id')
#         otp = data.get('otp')
        
#         if not approval_id or not otp:
#             return jsonify({"error": "Approval ID and OTP are required"}), 400
            
#         # Check if OTP exists and is valid
#         if approval_id not in otp_store:
#             return jsonify({"error": "OTP not found or expired"}), 400
            
#         stored_otp_data = otp_store[approval_id]
        
#         # Check expiration
#         if datetime.utcnow() > stored_otp_data['expires_at']:
#             del otp_store[approval_id]
#             return jsonify({"error": "OTP expired"}), 400
            
#         # Verify OTP
#         if stored_otp_data['otp'] != otp:
#             return jsonify({"error": "Invalid OTP"}), 400
            
#         # OTP is valid - remove it from store
#         del otp_store[approval_id]
        
#         return jsonify({
#             "message": "OTP verified successfully",
#             "valid": True
#         }), 200
        
#     except Exception as e:
#         print(f"Error verifying OTP: {str(e)}")
#         return jsonify({"error": "Failed to verify OTP"}), 500

# def send_otp_email(email, otp, approval_id):
#     """
#     Implement your email sending function here
#     This should send an email with the OTP to the user
#     """
#     try:
#         # Your email sending implementation
#         subject = "Your Approval OTP Code"
#         body = f"""
#         <h3>Notice Approval OTP</h3>
#         <p>Your OTP for notice approval is: <strong>{otp}</strong></p>
#         <p>This OTP will expire in 5 minutes.</p>
#         <p>Approval ID: {approval_id}</p>
#         <p>If you didn't request this, please ignore this email.</p>
#         """
        
#         # Use your existing email sending function
#         send_bulk_email([email], subject, body)
#         print(f"OTP email sent to {email}")
        
#     except Exception as e:
#         print(f"Error sending OTP email: {str(e)}")
#         raise e





















from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime,timedelta
from ..models.notice_model import Notice
from ..models.approval_model import Approval
from ..models.employee_model import Employee
from ..middleware.auth_middleware import token_required
from ..utils.email_send_function import send_bulk_email
import traceback
import random
import string
from ..extensions import socketio

otp_store = {}  # In-memory store for OTPs; in production, use a persistent store like Redis

approval_bp = Blueprint('approvals', __name__, url_prefix='/api/approvals')



@approval_bp.route('/request', methods=['POST'])
@token_required
def request_approval(current_user):
    try:
        data = request.get_json()
        notice_id = data.get('notice_id')
        
        if not notice_id:
            return jsonify({"error": "Notice ID is required"}), 400
            
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
        
        # Check if notice already has an approval workflow
        if notice.approval_workflow and len(notice.approval_workflow) > 0:
            return jsonify({
                "success": False,
                "error": "Approval already requested for this notice",
                "notice_id": str(notice.id),
                "redirect_url": f"/approval-tracking/{str(notice.id)}"
            }), 400
        
        # Get ALL employees (excluding students) as approvers
        approvers = Employee.objects(role__ne="student").all()
        
        if not approvers:
            # Auto-approve if no approvers found
            notice.update(
                approval_status="approved",
                status="published",
                requires_approval=False,
                approved_by=str(current_user.id),
                approved_by_name=current_user.name,
                approved_at=datetime.utcnow(),
                approval_comments="Auto-approved (no approvers found)"
            )
            return jsonify({
                "success": True,
                "message": "No approvers found, notice approved automatically",
                "notice_id": str(notice.id),
                "auto_approved": True,
                "redirect_url": f"/notices"  # Redirect to notices list since it's auto-approved
            }), 200
            
        # Create approval records for each approver
        approval_ids = []
        for approver in approvers:
            approval = Approval(
                notice_id=notice,  # Pass the Notice object
                approver_id=str(approver.id),
                approver_name=approver.name,
                approver_role=approver.role,
                approver_department=approver.department,
                status="pending"
            ).save()
            approval_ids.append(str(approval.id))
            
        # Update the notice with approval workflow
        notice.update(
            set__approval_workflow=approval_ids,
            set__approval_status="pending",
            set__status="pending_approval"
        )
        
        return jsonify({
            "success": True,
            "message": f"Approval request sent to {len(approvers)} employees.",
            "notice_id": str(notice.id),
            "approvers_count": len(approvers),
            "approval_ids": approval_ids,
            "redirect_url": f"/approval-tracking/{str(notice.id)}"  # Add redirect URL
        }), 200
        
    except Exception as e:
        print(f"Error in request_approval: {str(e)}")
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to request approval"
        }), 500

@approval_bp.route('/my', methods=['GET'])
@token_required
def get_my_approvals(current_user):
    try:
        print(f"Fetching approvals for user: {current_user.id}, {current_user.name}")
        
        # Get approvals for the current user
        approvals = Approval.objects(approver_id=str(current_user.id)).order_by('-created_at')
        
        print(f"Found {approvals.count()} approvals in database")
        
        # Prepare response data
        approvals_data = []
        for approval in approvals:
            print(f"Processing approval: {approval.id}, status: {approval.status}")
            
            # Get the associated notice - With ReferenceField, notice_id is the Notice object
            try:
                notice = approval.notice_id
                if not notice:
                    print(f"Notice not found for approval {approval.id}")
                    continue
                    
                print(f"Found notice: {notice.title}")
                
                approval_data = {
                    "_id": str(approval.id),
                    "notice_id": str(notice.id),
                    "status": approval.status,
                    "comments": approval.comments,
                    "createdAt": approval.created_at.isoformat(),
                    "approvedAt": approval.approved_at.isoformat() if approval.approved_at else None,
                    "approver_name": approval.approver_name,
                    "approver_role": approval.approver_role,
                    "approved_by_name": approval.approved_by_name,
                    "notice": {
                        "_id": str(notice.id),
                        "title": notice.title,
                        "content": notice.content,
                        "notice_type": notice.notice_type,
                        "attachments": notice.attachments or [],
                        "created_at": notice.created_at.isoformat() if notice.created_at else None,
                        "approval_status": notice.approval_status
                    }
                }
                
                approvals_data.append(approval_data)
                print(f"Added approval to response: {approval.id}")
                
            except Exception as e:
                print(f"Error processing approval {approval.id}: {str(e)}")
                continue
                
        print(f"Returning {len(approvals_data)} approvals in response")
        
        return jsonify({
            "success": True,
            "approvals": approvals_data,
            "count": len(approvals_data)
        }), 200
        
    except Exception as e:
        print(f"Error in get_my_approvals: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to fetch approvals",
            "approvals": [],
            "count": 0
        }), 500

@approval_bp.route('/<approval_id>/approve', methods=['POST'])
@token_required
def approve_notice(current_user, approval_id):
    try:
        # Check if OTP verification is required
        data = request.get_json()
        otp = data.get("otp")
        comments = data.get("comments", "")
        
        # If OTP is provided, verify it first
        if otp:
            # Verify OTP before proceeding with approval
            if approval_id not in otp_store:
                return jsonify({"error": "OTP not found or expired. Please request a new OTP."}), 400
                
            stored_otp_data = otp_store[approval_id]
            
            # Check expiration
            if datetime.utcnow() > stored_otp_data['expires_at']:
                del otp_store[approval_id]
                return jsonify({"error": "OTP expired. Please request a new OTP."}), 400
                
            # Verify OTP matches
            if stored_otp_data['otp'] != otp:
                return jsonify({"error": "Invalid OTP. Please try again."}), 400
                
            # OTP is valid - remove it from store
            del otp_store[approval_id]
        
        # If no OTP provided but OTP verification is required for this user/approval
        # You can add additional checks here if needed
        # For example: if current_user.requires_otp and not otp:
        #     return jsonify({"error": "OTP verification required"}), 400
        
        approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
        if not approval:
            return jsonify({"error": "Approval not found"}), 404
            
        if approval.status != "pending":
            return jsonify({"error": "Approval already processed"}), 400
        
        # Update approval record
        approval.update(
            status="approved",
            approved_at=datetime.utcnow(),
            comments=comments,
            approved_by_name=current_user.name,
            approved_by_role=current_user.role
        )
        
        # Get the notice and approve it immediately
        notice = approval.notice_id
        if notice:
            notice.update(
                approval_status="approved",
                status="published",
                approved_by=str(current_user.id),
                approved_by_name=current_user.name,
                approved_at=datetime.utcnow(),
                approval_comments=f"Approved by {current_user.name} ({current_user.role})"
            )
                
        return jsonify({
            "message": "Notice approved successfully",
            "approved_by": current_user.name,
            "approved_at": datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error in approve_notice: {str(e)}")
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/<approval_id>/reject', methods=['POST'])
@token_required
def reject_notice(current_user, approval_id):
    try:
        approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
        if not approval:
            return jsonify({"error": "Approval not found"}), 404
            
        if approval.status != "pending":
            return jsonify({"error": "Approval already processed"}), 400
            
        data = request.get_json()
        reason = data.get("reason", "")
        if not reason:
            return jsonify({"error": "Reason is required for rejection"}), 400
            
        approval.update(
            status="rejected",
            approved_at=datetime.utcnow(),
            comments=reason,
            approved_by_name=current_user.name,
            approved_by_role=current_user.role
        )
        
        # Immediately reject the notice
        notice = approval.notice_id
        if notice:
            notice.update(
                approval_status="rejected",
                status="rejected",
                approved_by=str(current_user.id),
                approved_by_name=current_user.name,
                approved_at=datetime.utcnow(),
                rejection_reason=reason
            )
        
        return jsonify({"message": "Notice rejected"}), 200
    except Exception as e:
        print(f"Error in reject_notice: {str(e)}")
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/<approval_id>/sign', methods=['POST'])
@token_required
def sign_approval(current_user, approval_id):
    try:
        approval = Approval.objects(id=ObjectId(approval_id), approver_id=str(current_user.id)).first()
        if not approval:
            return jsonify({"error": "Approval not found"}), 404
            
        if approval.status != "pending":
            return jsonify({"error": "Approval must be pending to sign"}), 400
            
        data = request.get_json()
        signature_data = data.get("signature")
        if not signature_data:
            return jsonify({"error": "Signature data is required"}), 400
            
        # Save signature and approve
        approval.update(
            signature=signature_data,
            status="approved",
            approved_at=datetime.utcnow(),
            comments=data.get("comments", ""),
            approved_by_name=current_user.name,
            approved_by_role=current_user.role
        )
        
        # Get the notice and approve it immediately
        notice = approval.notice_id
        if notice:
            # Update notice status immediately
            notice.update(
                approval_status="approved",
                status="published",
                approved_by=str(current_user.id),
                approved_by_name=current_user.name,
                approved_at=datetime.utcnow(),
                approval_comments=f"Signed and approved by {current_user.name} ({current_user.role})"
            )
                
        return jsonify({
            "message": "Approval signed successfully",
            "approved_by": current_user.name
        }), 200
        
    except Exception as e:
        print(f"Error in sign_approval: {str(e)}")
        return jsonify({"error": str(e)}), 500
    








    # Add these routes to your approval_routes.py
@approval_bp.route('/track/<notice_id>', methods=['GET'])
@token_required
def get_approval_tracking(current_user, notice_id):
    """
    Get approval tracking information for a specific notice
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
            
        # Check if user has permission to view this notice
        if str(current_user.id) != notice.created_by and current_user.role not in ['admin', 'academic_head']:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Get all approval records for this notice
        approvals = []
        if hasattr(notice, 'approval_workflow') and notice.approval_workflow:
            for approval_id in notice.approval_workflow:
                try:
                    # Make sure we're converting string ID to ObjectId if needed
                    if isinstance(approval_id, str):
                        approval_id = ObjectId(approval_id)
                    
                    approval = Approval.objects(id=approval_id).first()
                    if approval:
                        approvals.append({
                            "id": str(approval.id),
                            "approver_name": approval.approver_name,
                            "approver_role": approval.approver_role,
                            "approver_department": approval.approver_department,
                            "status": approval.status,
                            "comments": approval.comments,
                            "created_at": approval.created_at.isoformat() if approval.created_at else None,
                            "approved_at": approval.approved_at.isoformat() if approval.approved_at else None,
                            "signature": approval.signature
                        })
                except Exception as e:
                    print(f"Error loading approval {approval_id}: {str(e)}")
                    continue
        
        # Get auto_publish_after_approval setting (with fallback)
        auto_publish = getattr(notice, 'auto_publish_after_approval', False)
        
        # Get approval_status (with fallback)
        approval_status = getattr(notice, 'approval_status', 'not_required')
        
        # Get created_by_name (with fallback)
        created_by_name = getattr(notice, 'created_by_name', 'Unknown')
        
        # Get created_by employee details (since employees create notices)
        try:
            created_by_employee = Employee.objects(id=ObjectId(notice.created_by)).first()
            if created_by_employee:
                created_by_name = getattr(created_by_employee, 'name', created_by_name)
        except:
            # If not found as employee, try as user (fallback)
            try:
                created_by_user = Employee.objects(id=ObjectId(notice.created_by)).first()
                if created_by_user:
                    created_by_name = getattr(created_by_user, 'name', created_by_name)
            except:
                pass  # Keep the default 'Unknown'
        
        # Get notice title with fallback
        notice_title = getattr(notice, 'title', 'Untitled Notice')
        
        # Get created_at with fallback
        created_at = getattr(notice, 'created_at', datetime.utcnow())
        
        # Get requires_approval with fallback
        requires_approval = getattr(notice, 'requires_approval', False)
        
        return jsonify({
            "success": True,
            "notice_id": str(notice.id),
            "notice_title": notice_title,
            "auto_publish_after_approval": auto_publish,
            "current_status": approval_status,
            "approvals": approvals,
            "created_at": created_at.isoformat() if hasattr(created_at, 'isoformat') else datetime.utcnow().isoformat(),
            "created_by": created_by_name,
            "requires_approval": requires_approval
        }), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "message": "Failed to fetch approval tracking data"
        }), 500

@approval_bp.route('/track/<notice_id>/settings', methods=['PUT'])
@token_required
def update_approval_settings(current_user, notice_id):
    """
    Update approval settings for a notice
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
            
        # Check if user has permission to modify this notice
        if str(current_user.id) != notice.created_by:
            return jsonify({"error": "Unauthorized"}), 403
            
        data = request.json
        auto_publish = data.get('auto_publish_after_approval', False)
        
        notice.update(auto_publish_after_approval=auto_publish)
        
        return jsonify({
            "message": "Settings updated successfully",
            "auto_publish_after_approval": auto_publish
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@approval_bp.route('/track/<notice_id>/publish', methods=['POST'])
@token_required
def manually_publish_notice(current_user, notice_id):
    """
    Manually publish a notice after approval
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
            
        # Check if user has permission to publish this notice
        if str(current_user.id) != notice.created_by:
            return jsonify({"error": "Unauthorized"}), 403
            
        # Check if notice is approved
        if notice.approval_status != 'approved':
            return jsonify({"error": "Notice must be approved before publishing"}), 400
            
        # Check if notice is already published
        if notice.status == 'published':
            return jsonify({"error": "Notice is already published"}), 400
            
        # Publish the notice
        notice.update(
            status='published',
            publish_at=datetime.datetime.utcnow()
        )
        
        # TODO: Send notifications to recipients
        
        return jsonify({
            "message": "Notice published successfully",
            "published_at": datetime.datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
  


# ////////////////////////  approval ////////////////////////

@approval_bp.route('/send-otp', methods=['POST'])
@token_required
def send_approval_otp(current_user):
    try:
        data = request.get_json()
        approval_id = data.get('approval_id')
        
        if not approval_id:
            return jsonify({"error": "Approval ID is required"}), 400
            
        # Use the current user's email from the token
        approver_email = current_user.email  # or current_user.official_email
        
        # Generate 6-digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store OTP with expiration (5 minutes)
        otp_store[approval_id] = {
            'otp': otp,
            'expires_at': datetime.utcnow() + timedelta(minutes=5),
            'email': approver_email
        }
        
        # Send email with OTP
        send_otp_email(approver_email, otp, approval_id)
        
        return jsonify({
            "message": "OTP sent successfully to your email",
            "expires_in": 300  # 5 minutes in seconds
        }), 200
        
    except Exception as e:
        print(f"Error sending OTP: {str(e)}")
        return jsonify({"error": "Failed to send OTP"}), 500

@approval_bp.route('/verify-otp', methods=['POST'])
@token_required
def verify_approval_otp(current_user):
    try:
        data = request.get_json()
        approval_id = data.get('approval_id')
        otp = data.get('otp')
        
        if not approval_id or not otp:
            return jsonify({"error": "Approval ID and OTP are required"}), 400
            
        # Check if OTP exists and is valid
        if approval_id not in otp_store:
            return jsonify({"error": "OTP not found or expired"}), 400
            
        stored_otp_data = otp_store[approval_id]
        
        # Check expiration
        if datetime.utcnow() > stored_otp_data['expires_at']:
            del otp_store[approval_id]
            return jsonify({"error": "OTP expired"}), 400
            
        # Verify OTP
        if stored_otp_data['otp'] != otp:
            return jsonify({"error": "Invalid OTP"}), 400
            
        # OTP is valid - remove it from store
        del otp_store[approval_id]
        
        return jsonify({
            "message": "OTP verified successfully",
            "valid": True
        }), 200
        
    except Exception as e:
        print(f"Error verifying OTP: {str(e)}")
        return jsonify({"error": "Failed to verify OTP"}), 500

def send_otp_email(email, otp, approval_id):
    """
    Implement your email sending function here
    This should send an email with the OTP to the user
    """
    try:
        # Your email sending implementation
        subject = "Your Approval OTP Code"
        body = f"""
        <h3>Notice Approval OTP</h3>
        <p>Your OTP for notice approval is: <strong>{otp}</strong></p>
        <p>This OTP will expire in 5 minutes.</p>
        <p>Approval ID: {approval_id}</p>
        <p>If you didn't request this, please ignore this email.</p>
        """
        
        # Use your existing email sending function
        send_bulk_email([email], subject, body)
        print(f"OTP email sent to {email}")
        
    except Exception as e:
        print(f"Error sending OTP email: {str(e)}")
        raise e