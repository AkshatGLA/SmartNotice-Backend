from flask import Blueprint, request, jsonify, send_file, current_app
from bson import ObjectId
import datetime
import json
import os
import traceback
from werkzeug.utils import secure_filename
from ..models.notice_model import Notice
from ..models.user_model import User
from ..models.student_model import Student
from ..models.department_model import Department
from ..models.employee_model import Employee
from ..middleware.auth_middleware import token_required, role_required
from ..utils.email_send_function import send_bulk_email
from ..models.approval_model import Approval
# from ..models.notification_model import Notification
from ..extensions import socketio

notice_bp = Blueprint('notices', __name__, url_prefix='/api/notices')

UPLOAD_FOLDER = 'uploads'



def emit_notice_read(read_data):
    """Emit notice read updates to all connected clients"""
    try:
        if socketio and hasattr(socketio, 'emit'):
            socketio.emit('notice_read_update', read_data, namespace='/notices')
            current_app.logger.info(f"Emitted notice_read_update: {read_data}")
    except Exception as e:
        current_app.logger.error(f"Error emitting notice_read_update: {str(e)}")

def emit_notice_update(event_type, notice_data):
    """Emit notice updates to all connected clients"""
    try:
        if socketio and hasattr(socketio, 'emit'):
            socketio.emit('notice_update', {
                'type': event_type,
                'data': notice_data
            }, namespace='/notices')
            current_app.logger.info(f"Emitted notice_update event: {event_type} - {notice_data}")
        else:
            current_app.logger.warning("SocketIO not available for emitting notice_update")
    except Exception as e:
        current_app.logger.error(f"Error emitting notice_update: {str(e)}")
        traceback.print_exc()

def emit_notice_read(notice_id, user_id, read_count):
    """Emit notice read updates to all connected clients"""
    try:
        if socketio and hasattr(socketio, 'emit'):
            socketio.emit('notice_read_update', {
                'noticeId': str(notice_id),
                'userId': str(user_id),
                'readCount': read_count,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, namespace='/notices')
            current_app.logger.info(f"Emitted notice_read_update: {notice_id}, {user_id}, {read_count}")
    except Exception as e:
        current_app.logger.error(f"Error emitting notice_read_update: {str(e)}")

def emit_analytics_update():
    """Emit general analytics updates"""
    try:
        if socketio and hasattr(socketio, 'emit'):
            total_notices = Notice.objects.count()
            total_reads = sum(notice.read_count for notice in Notice.objects())
            
            socketio.emit('analytics_update', {
                'totalNotices': total_notices,
                'totalReads': total_reads,
                'timestamp': datetime.datetime.utcnow().isoformat()
            }, namespace='/notices', room='analytics')
    except Exception as e:
        current_app.logger.error(f"Error emitting analytics_update: {str(e)}")

@socketio.on('join_analytics_room', namespace='/notices')
def handle_join_analytics_room(data):
    """Handle clients joining the analytics room"""
    try:
        from flask_socketio import join_room
        join_room('analytics')
        current_app.logger.info(f"Client joined analytics room: {request.sid}")
        socketio.emit('connected', {'message': 'Joined analytics room'}, 
                     namespace='/notices', room=request.sid)
    except Exception as e:
        current_app.logger.error(f"Error joining analytics room: {str(e)}")

@socketio.on('leave_analytics_room', namespace='/notices')
def handle_leave_analytics_room(data):
    """Handle clients leaving the analytics room"""
    try:
        from flask_socketio import leave_room
        leave_room('analytics')
        current_app.logger.info(f"Client left analytics room: {request.sid}")
    except Exception as e:
        current_app.logger.error(f"Error leaving analytics room: {str(e)}")

@socketio.on('join_notice_room', namespace='/notices')
def handle_join_notice_room(data):
    """Handle clients joining a specific notice room"""
    try:
        from flask_socketio import join_room
        notice_id = data.get('notice_id')
        if notice_id:
            join_room(f'notice_{notice_id}')
            current_app.logger.info(f"Client joined notice room {notice_id}: {request.sid}")
    except Exception as e:
        current_app.logger.error(f"Error joining notice room: {str(e)}")

@socketio.on('leave_notice_room', namespace='/notices')
def handle_leave_notice_room(data):
    """Handle clients leaving a specific notice room"""
    try:
        from flask_socketio import leave_room
        notice_id = data.get('notice_id')
        if notice_id:
            leave_room(f'notice_{notice_id}')
            current_app.logger.info(f"Client left notice room {notice_id}: {request.sid}")
    except Exception as e:
        current_app.logger.error(f"Error leaving notice room: {str(e)}")


@notice_bp.route("", methods=["GET"])
@token_required
def get_notices(current_user):
    try:
        notices = Notice.objects().order_by('-created_at')
        user_map = {str(user.id): user for user in User.objects.only('id', 'name', 'email')}

        notices_data = []
        for notice in notices:
            creator = user_map.get(notice.created_by)
            notices_data.append({
                "id": str(notice.id),
                "title": notice.title,
                "subject": notice.subject,
                "content": notice.content,
                "notice_type": notice.notice_type,
                "departments": notice.departments,
                "program_course": notice.program_course,
                "specialization": notice.specialization,
                "year": notice.year,
                "section": notice.section,
                "priority": notice.priority,  # ADDED: Priority field
                "status": notice.status,
                "from_field": notice.from_field,
                "publish_at": notice.publish_at.isoformat() if notice.publish_at else None,
                "created_at": notice.created_at.isoformat(),
                "read_count": notice.read_count,
                "requires_approval": notice.requires_approval,
                "approval_status": notice.approval_status,
                "approved_by_name": notice.approved_by_name,
                "approved_at": notice.approved_at.isoformat() if notice.approved_at else None,
                "createdBy": {
                    "id": notice.created_by,
                    "name": creator.name if creator else "Unknown",
                    "email": creator.email if creator else ""
                },
                "attachments": notice.attachments or []
            })

        return jsonify(notices_data), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@notice_bp.route("", methods=["POST"])
@token_required
def create_notice(current_user):
    try:
        form_data = request.form
        files = request.files.getlist('attachments')

        # Handle attachments
        attachment_filenames = []
        attachment_paths = []
        if files:
            if not os.path.exists(UPLOAD_FOLDER):
                os.makedirs(UPLOAD_FOLDER)
            for file in files:
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    attachment_paths.append(file_path)
                    attachment_filenames.append(filename)

        # Get form data - ADDED: Priority field
        requires_approval = form_data.get('requires_approval', 'false').lower() == 'true'
        status = form_data.get('status', 'draft')
        priority = form_data.get('priority', 'Normal')  # ADDED: Priority field
        
        # Determine status based on approval requirement
        if status == 'published' and requires_approval:
            status = 'pending_approval'
            approval_status = 'pending'
        elif status == 'published' and not requires_approval:
            approval_status = 'approved'
        else:
            approval_status = 'not_required'

        # Create notice with all fields - ADDED: Priority field
        notice = Notice(
            title=form_data.get('title'),
            subject=form_data.get('subject', ''),
            content=form_data.get('content'),
            notice_type=form_data.get('notice_type', ''),
            departments=json.loads(form_data.get('departments', '[]')),
            program_course=form_data.get('program_course', ''),
            year=form_data.get('year', ''),
            section=form_data.get('section', ''),
            recipient_emails=json.loads(form_data.get('recipient_emails', '[]')),
            priority=priority,  # ADDED: Priority field
            send_options=json.loads(form_data.get('send_options', '{"email": false, "web": true}')),
            status=status,
            approval_status=approval_status,
            requires_approval=requires_approval,
            from_field=form_data.get('from_field', current_user.name),
            created_by=str(current_user.id),
            created_by_name=current_user.name,
            attachments=attachment_filenames,
            created_at=datetime.datetime.utcnow()
        ).save()

        # CREATE APPROVALS IF REQUIRED
        if requires_approval and status == 'pending_approval':
            approvers = Employee.objects(role__ne="student").all()
            
            if not approvers:
                notice.update(
                    approval_status="approved",
                    status="published",
                    requires_approval=False,
                    approved_by=str(current_user.id),
                    approved_by_name=current_user.name,
                    approved_at=datetime.datetime.utcnow()
                )
            else:
                approval_ids = []
                for approver in approvers:
                    approval = Approval(
                        notice_id=notice.id,
                        approver_id=str(approver.id),
                        approver_name=approver.name,
                        approver_role=approver.role,
                        approver_department=approver.department,
                        status="pending"
                    ).save()
                    approval_ids.append(approval.id)
                
                notice.update(
                    set__approval_workflow=approval_ids,
                    set__approval_status="pending"
                )

        # Clean up attachments
        for path in attachment_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error cleaning up attachment {path}: {e}")

        # Emit real-time update
        notice_data = {
            "id": str(notice.id),
            "title": notice.title,
            "status": notice.status,
            "approval_status": notice.approval_status,
            "created_by": current_user.name,
            "created_at": notice.created_at.isoformat(),
            "notice_type": notice.notice_type,
            "priority": notice.priority  # ADDED: Priority field
        }
        emit_notice_update('created', notice_data)
        
        response_data = {
            "message": "Notice created successfully",
            "noticeId": str(notice.id),
            "requiresApproval": requires_approval,
            "status": status,
            "approvalStatus": approval_status,
            "priority": priority  # ADDED: Priority field
        }
        
        return jsonify(response_data), 201
        
    except Exception as e:
        traceback.print_exc()
        if 'attachment_paths' in locals():
            for path in attachment_paths:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/my", methods=["GET"])
@token_required
def get_my_notices(current_user):
    try:
        # Determine user type and fetch their document
        if hasattr(current_user, 'univ_roll_no'):  # Student
            user = Student.objects(id=current_user.id).only('notices').first()
        else:  # Employee
            user = Employee.objects(id=current_user.id).only('notices').first()
            
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Extract just the Notice IDs from the user's notices list
        notice_ids = [notice.id for notice in user.notices]

        # Get all notices for this user (sorted by creation date)
        notices = Notice.objects(id__in=notice_ids).order_by('-created_at')
        
        # Get creator information in bulk for efficiency
        creator_ids = list({notice.created_by for notice in notices})
        creators = {str(user.id): user for user in User.objects(id__in=creator_ids).only('id', 'name', 'email')}
        
        # Prepare response data with all necessary fields
        notices_data = []
        for notice in notices:
            creator = creators.get(notice.created_by)
            notices_data.append({
                "id": str(notice.id),
                "title": notice.title,
                "subject": notice.subject,
                "content": notice.content,
                "notice_type": notice.notice_type,
                "priority": notice.priority,
                "created_at": notice.created_at.isoformat(),
                "attachments": notice.attachments or [],
                "from_field": notice.from_field,
                "approval_status": notice.approval_status,
                "approved_by_name": notice.approved_by_name,
                "approved_at": notice.approved_at.isoformat() if notice.approved_at else None,
                "createdBy": {
                    "id": notice.created_by,
                    "name": creator.name if creator else "Unknown",
                    "email": creator.email if creator else ""
                },
                "departments": notice.departments,
                "program_course": notice.program_course,
                "year": notice.year,
                "section": notice.section,
                "status": notice.status
            })
        
        return jsonify(notices_data), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch notices", "details": str(e)}), 500

@notice_bp.route("/<notice_id>", methods=["GET"])
@token_required
def get_notice(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
        
        creator = User.objects(id=ObjectId(notice.created_by)).first()
        
        # Build response with all model fields
        notice_data = {
            "id": str(notice.id),
            "title": notice.title,
            "subject": notice.subject,
            "content": notice.content,
            "notice_type": notice.notice_type,
            "departments": notice.departments,
            "program_course": notice.program_course,
            "specialization": notice.specialization,
            "year": notice.year,
            "section": notice.section,
            "recipient_emails": notice.recipient_emails,
            "priority": notice.priority,
            "status": notice.status,
            "send_options": notice.send_options,
            "from_field": notice.from_field,
            "publish_at": notice.publish_at.isoformat() if notice.publish_at else None,
            "created_at": notice.created_at.isoformat(),
            "updated_at": notice.updated_at.isoformat(),
            "read_count": notice.read_count,
            "requires_approval": notice.requires_approval,
            "approval_status": notice.approval_status,
            "rejection_reason": notice.rejection_reason,
            "approved_by": notice.approved_by,
            "approved_by_name": notice.approved_by_name,
            "approved_at": notice.approved_at.isoformat() if notice.approved_at else None,
            "approval_comments": notice.approval_comments,
            "createdBy": {
                "id": notice.created_by,
                "name": creator.name if creator else "Unknown",
                "email": creator.email if creator else ""
            },
            "attachments": notice.attachments
        }
        
        return jsonify(notice_data), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/<notice_id>", methods=["PUT"])
@token_required
@role_required(['academic'])
def update_notice(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id), created_by=str(current_user.id)).first()
        if not notice:
            return jsonify({"error": "Notice not found or unauthorized"}), 404
            
        form_data = request.form
        
        # Update fields
        notice.title = form_data.get('title', notice.title)
        notice.subject = form_data.get('subject', notice.subject)
        notice.content = form_data.get('content', notice.content)
        notice.notice_type = form_data.get('noticeType', notice.notice_type)
        notice.departments = json.loads(form_data.get('departments', json.dumps(notice.departments)))
        notice.program_course = form_data.get('programCourse', notice.program_course)
        notice.specialization = form_data.get('specialization', notice.specialization)
        notice.year = form_data.get('year', notice.year)
        notice.section = form_data.get('section', notice.section)
        notice.recipient_emails = json.loads(form_data.get('recipient_emails', json.dumps(notice.recipient_emails)))
        notice.priority = form_data.get('priority', notice.priority)
        notice.send_options = json.loads(form_data.get('send_options', json.dumps(notice.send_options)))
        notice.status = form_data.get('status', notice.status)
        
        # Handle file attachments
        attachment_paths = []
        if 'attachments' in request.files:
            for file in request.files.getlist('attachments'):
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(UPLOAD_FOLDER, filename)
                    file.save(file_path)
                    attachment_paths.append(file_path)
                    notice.attachments.append(filename)

        notice.updated_at = datetime.datetime.now()
        notice.save()
        
        # Send email if the notice is published and has recipients
        if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
            send_bulk_email(
                recipient_emails=notice.recipient_emails,
                subject=notice.subject or notice.title,
                body=notice.content,
                attachments=attachment_paths
            )
        
        # Emit real-time update
        notice_data = {
            "id": str(notice.id),
            "title": notice.title,
            "status": notice.status,
            "updated_at": notice.updated_at.isoformat()
        }
        emit_notice_update('updated', notice_data)
        
        # Clean up attachments
        for path in attachment_paths:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception as e:
                    print(f"Error cleaning up attachment {path}: {e}")
        
        return jsonify({"message": "Notice updated successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

@notice_bp.route("/<notice_id>", methods=["DELETE"])
@token_required
@role_required(['academic'])
def delete_notice(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
        
        # Emit real-time update before deletion
        notice_data = {
            "id": str(notice.id),
            "title": notice.title
        }
        emit_notice_update('deleted', notice_data)
            
        notice.delete()
        
        # Also emit analytics update
        emit_analytics_update()
        
        return jsonify({"message": "Notice deleted successfully"}), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



@notice_bp.route("/<notice_id>/read", methods=["POST"])
@token_required
def mark_notice_read(current_user, notice_id):
    """
    Tracks every time a user opens/reads a notice.
    Increments read count for each user visit.
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        user_id = str(current_user.id)
        now = datetime.datetime.utcnow()

        # Initialize reads array if it doesn't exist
        if not hasattr(notice, 'reads') or notice.reads is None:
            notice.reads = []

        # Find existing read record for this user
        existing_read = None
        read_index = None
        
        for i, read in enumerate(notice.reads):
            if read.get('user_id') == user_id:
                existing_read = read
                read_index = i
                break

        if existing_read:
            # User has read before - increment their read count
            updated_read_count = existing_read.get('read_count', 1) + 1
            
            # Create updated read record
            updated_read = {
                "user_id": user_id,
                "read_count": updated_read_count,
                "first_read_at": existing_read.get('first_read_at', existing_read.get('timestamp', now)),
                "last_read_at": now,
                "total_time_spent": existing_read.get('total_time_spent', 0)
            }
            
            # Update the specific read record in the array
            notice.reads[read_index] = updated_read
            notice.save()
            
            # EMIT SOCKET EVENT FOR READ UPDATE - FIXED CALL
            emit_notice_read(notice.id, user_id, updated_read_count)
            
            return jsonify({
                "message": f"Read count updated to {updated_read_count}",
                "isNewRead": False,
                "readCount": updated_read_count,
                "totalUniqueReaders": len(notice.reads)
            }), 200
            
        else:
            # First time this user is reading - add new read record
            new_read = {
                "user_id": user_id,
                "read_count": 1,
                "first_read_at": now,
                "last_read_at": now,
                "total_time_spent": 0
            }
            
            # Add to reads array and increment unique reader count
            notice.update(
                push__reads=new_read,
                inc__read_count=1  # This tracks unique readers
            )
            
            # EMIT SOCKET EVENT FOR NEW READ - FIXED CALL
            emit_notice_read(notice.id, user_id, 1)
            
            return jsonify({
                "message": "First read recorded",
                "isNewRead": True,
                "readCount": 1,
                "totalUniqueReaders": notice.read_count + 1
            }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to track read: {str(e)}"}), 500


@notice_bp.route("/<notice_id>/reads", methods=["GET"])
@token_required
def get_notice_reads(current_user, notice_id):
    """
    Get detailed reading analytics for a notice.
    Shows how many times each user has read the notice.
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        # Handle case where reads might not exist or be empty
        if not hasattr(notice, 'reads') or not notice.reads:
            return jsonify({
                "notice_title": notice.title,
                "total_reads": 0,
                "unique_readers": 0,
                "average_reads_per_user": 0,
                "reads": []
            }), 200

        # Extract user IDs from reads
        user_ids = [read['user_id'] for read in notice.reads if 'user_id' in read]

        # Get all students in bulk
        students = Student.objects(id__in=user_ids).only(
            'id', 'name', 'univ_roll_no', 'branch', 
            'course', 'section', 'official_email'
        )
        student_map = {str(s.id): s for s in students}

        # Also try to get employees if students not found
        if len(student_map) < len(user_ids):
            missing_ids = [uid for uid in user_ids if uid not in student_map]
            employees = Employee.objects(id__in=missing_ids).only(
                'id', 'name', 'email', 'department'
            )
            for emp in employees:
                student_map[str(emp.id)] = emp

        # Prepare response data
        reads_data = []
        total_reads = 0
        
        for read in notice.reads:
            user_id = read['user_id']
            user = student_map.get(user_id)
            if not user:
                continue
                
            read_count = read.get('read_count', 1)
            total_reads += read_count
            
            # Handle both old and new data structures
            first_read = read.get('first_read_at') or read.get('timestamp')
            last_read = read.get('last_read_at') or read.get('timestamp')
            
            # Check if it's a student or employee
            if hasattr(user, 'univ_roll_no'):  # Student
                reads_data.append({
                    "student_id": user_id,
                    "student_name": user.name,
                    "roll_number": user.univ_roll_no,
                    "department": user.branch,
                    "course": user.course,
                    "section": user.section,
                    "email": user.official_email,
                    "read_count": read_count,
                    "first_read": first_read.isoformat() if first_read else None,
                    "last_read": last_read.isoformat() if last_read else None,
                    "total_time_spent": read.get('total_time_spent', 0),
                    "user_type": "student"
                })
            else:  # Employee
                reads_data.append({
                    "student_id": user_id,
                    "student_name": user.name,
                    "roll_number": "N/A",
                    "department": getattr(user, 'department', 'N/A'),
                    "course": "Employee",
                    "section": "N/A",
                    "email": user.email,
                    "read_count": read_count,
                    "first_read": first_read.isoformat() if first_read else None,
                    "last_read": last_read.isoformat() if last_read else None,
                    "total_time_spent": read.get('total_time_spent', 0),
                    "user_type": "employee"
                })

        # Sort by read count (descending), then by last read time
        # Sort by read count (descending), then by last read time
        reads_data.sort(key=lambda x: (x['read_count'], x['last_read'] or ''), reverse=True)

        return jsonify({
            "notice_title": notice.title,
            "total_reads": total_reads,  # Sum of all read counts (total interactions)
            "unique_readers": len(reads_data),  # Number of unique users who read
            "average_reads_per_user": round(total_reads / len(reads_data), 1) if reads_data else 0,
            "most_active_reader": {
                "name": reads_data[0]["student_name"],
                "read_count": reads_data[0]["read_count"]
            } if reads_data else None,
            "high_engagement_users": len([r for r in reads_data if r['read_count'] >= 5]),
            "reads": reads_data
        }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to get reads: {str(e)}"}), 500


@notice_bp.route("/<notice_id>/my-reads", methods=["GET"])
@token_required
def get_my_read_count(current_user, notice_id):
    """
    Get the current user's read count for a specific notice.
    """
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        user_id = str(current_user.id)
        
        # Find user's read record
        user_read = None
        if hasattr(notice, 'reads') and notice.reads:
            for read in notice.reads:
                if read.get('user_id') == user_id:
                    user_read = read
                    break

        if user_read:
            return jsonify({
                "hasRead": True,
                "readCount": user_read.get('read_count', 1),
                "firstReadAt": user_read.get('first_read_at', user_read.get('timestamp')).isoformat() if user_read.get('first_read_at') or user_read.get('timestamp') else None,
                "lastReadAt": user_read.get('last_read_at', user_read.get('timestamp')).isoformat() if user_read.get('last_read_at') or user_read.get('timestamp') else None
            }), 200
        else:
            return jsonify({
                "hasRead": False,
                "readCount": 0,
                "firstReadAt": None,
                "lastReadAt": None
            }), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to get read count: {str(e)}"}), 500


@notice_bp.route("/<notice_id>/analytics", methods=["GET"])
@token_required
def get_notice_analytics(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
            
        analytics_data = {
            "recipientCount": len(notice.recipient_emails) if notice.recipient_emails else 0,
            "priority": notice.priority,
            "status": notice.status,
            "publishedAt": notice.publish_at.isoformat() if notice.publish_at else None,
            "createdAt": notice.created_at.isoformat(),
            "attachmentsCount": len(notice.attachments) if notice.attachments else 0,
            "readPercentage": (notice.read_count / len(notice.recipient_emails)) * 100 if notice.recipient_emails else 0
        }
        
        return jsonify(analytics_data), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch analytics"}), 500

@notice_bp.route("/analytics", methods=["GET"])
@token_required
@role_required(['academic'])
def get_all_notices_analytics(current_user):
    try:
        total_notices = Notice.objects.count()
        total_reads = sum(notice.read_count for notice in Notice.objects())
        
        return jsonify({
            "totalNotices": total_notices,
            "totalReads": total_reads,
            "averageReadsPerNotice": total_reads / total_notices if total_notices > 0 else 0
        }), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/created-by/<user_id>", methods=["GET"])
@token_required
def get_notices_by_creator(current_user, user_id):
    try:
        # Verify the requesting user has permission
        if current_user.role != "academic" and str(current_user.id) != user_id:
            return jsonify({"error": "Unauthorized"}), 403

        notices = Notice.objects(created_by=user_id).order_by('-created_at')
        
        user_map = {str(user.id): user for user in User.objects.only('id', 'name', 'email')}
        
        notices_data = []
        for notice in notices:
            creator = user_map.get(notice.created_by)
            notices_data.append({
                "id": str(notice.id),
                "title": notice.title,
                "content": notice.content,
                "notice_type": notice.notice_type,
                "departments": notice.departments,
                "year": notice.year,
                "section": notice.section,
                "recipient_emails": notice.recipient_emails,
                "priority": notice.priority,
                "status": notice.status,
                "from_field": notice.from_field,
                "approval_status": notice.approval_status,
                "approved_by_name": notice.approved_by_name,
                "approved_at": notice.approved_at.isoformat() if notice.approved_at else None,
                "approval_comments": notice.approval_comments,
                "publish_at": notice.publish_at.isoformat() if notice.publish_at else None,
                "created_at": notice.created_at.isoformat(),
                "updated_at": notice.updated_at.isoformat(),
                "created_by": {
                    "id": notice.created_by,
                    "name": creator.name if creator else "Unknown",
                    "email": creator.email if creator else ""
                },
                "attachments": notice.attachments
            })
            
        return jsonify(notices_data), 200
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Failed to fetch notices",
            "details": str(e)
        }), 500

@notice_bp.route('/departments', methods=['GET'])
@token_required
def get_departments(current_user):
    """
    Fetches a list of all departments.
    """
    try:
        departments = Department.objects.only('name', 'code').order_by('name')
        return jsonify([{"name": d.name, "code": d.code} for d in departments]), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    


@notice_bp.route('/courses-by-departments', methods=['POST'])
@token_required
def get_courses_by_departments(current_user):
    """
    Fetches courses based on a list of selected department codes.
    """
    try:
        data = request.json
        dept_codes = data.get('departments', [])
        if not dept_codes:
            return jsonify([]), 200

        departments = Department.objects(code__in=dept_codes)
        
        all_courses = {} 
        for dept in departments:
            for course in dept.courses:
                if course.code not in all_courses:
                    all_courses[course.code] = {"name": course.name, "value": course.name}
        
        sorted_courses = sorted(list(all_courses.values()), key=lambda c: c['name'])
        
        return jsonify(sorted_courses), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notice_bp.route('/years', methods=['GET'])
@token_required
def get_years(current_user):
    """
    Fetches distinct years from the student collection based on department and course.
    """
    try:
        department_names = request.args.getlist('department')
        course_names = request.args.getlist('course')
        
        query = {}
        if department_names: query['branch__in'] = department_names
        if course_names: query['course__in'] = course_names
        
        years = Student.objects(**query).distinct('year')
        sorted_years = sorted([y for y in years if y])
        return jsonify(sorted_years), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notice_bp.route('/sections', methods=['GET'])
@token_required
def get_sections(current_user):
    """
    Fetches distinct sections based on department, course, and year.
    """
    try:
        department_names = request.args.getlist('department')
        course_names = request.args.getlist('course')
        years = request.args.getlist('year')
        
        query = {}
        if department_names: query['branch__in'] = department_names
        if course_names: query['course__in'] = course_names
        if years: query['year__in'] = years
        
        sections = Student.objects(**query).distinct('section')
        sorted_sections = sorted([s for s in sections if s])
        return jsonify(sorted_sections), 200
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/predict-priority", methods=["POST"])
@token_required
def predict_priority(current_user):
    """
    Predicts the priority of a notice using a pre-trained ML model.
    """
    try:
        data = request.json
        subject = data.get("subject", "")
        body = data.get("body", "")

        if not subject and not body:
            return jsonify({"error": "Subject or body is required"}), 400

        # Manual model loading to avoid TensorFlow import
        MODEL_PATH = "C:\\Users\\Aryan\\Downloads\\roberta_priority_classifier_final-20250903T183036Z-1-001\\roberta_priority_classifier_final"
        
        # Check what files are in the model directory
        import os
        model_files = os.listdir(MODEL_PATH)
        print("Model files:", model_files)
        
        # If there's a PyTorch model file, use it
        if 'pytorch_model.bin' in model_files:
            from transformers import RobertaForSequenceClassification, RobertaTokenizer
            import torch
            
            tokenizer = RobertaTokenizer.from_pretrained(MODEL_PATH)
            model = RobertaForSequenceClassification.from_pretrained(MODEL_PATH)
            model.eval()
            
            label_map = {0: "Normal", 1: "Urgent", 2: "Highly Urgent"}
            full_text = f"{subject} {body}"
            
            inputs = tokenizer(full_text, return_tensors="pt", truncation=True, padding=True, max_length=512)
            
            with torch.no_grad():
                outputs = model(**inputs)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_class = torch.argmax(predictions, dim=1).item()
            
            priority = label_map.get(predicted_class, "Normal")
            
        else:
            # Fallback: return a default priority or error
            priority = "Normal"  # Default fallback
            # return jsonify({"error": "TensorFlow model detected but TensorFlow is not working"}), 500

        return jsonify({"priority": priority}), 200
        
    except Exception as e:
        traceback.print_exc()
        # Fallback to default priority instead of error
        return jsonify({"priority": "Normal"}), 200