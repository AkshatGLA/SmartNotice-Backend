from flask import Blueprint, request, jsonify, send_file,current_app
from bson import ObjectId
import datetime
import json
import os
from werkzeug.utils import secure_filename
from ..models.notice_model import Notice
from ..models.user_model import User
from ..models.student_model import Student
from ..middleware.auth_middleware import token_required, role_required
from ..utils.email_send_function import send_bulk_email
from ..models.employee_model import Employee
# from ..models.notification_model import Notification
# from ..extensions import socketio

notice_bp = Blueprint('notices', __name__, url_prefix='/api/notices')

@notice_bp.route("", methods=["GET"])
@token_required
# @role_required(['admin'])  # Only admins can access this endpoint
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
                "programCourse": notice.program_course,
                "specialization": notice.specialization,
                "year": notice.year,
                "section": notice.section,
                "priority": notice.priority,
                "status": notice.status,
                "publishAt": notice.publish_at.isoformat() if notice.publish_at else None,
                "createdAt": notice.created_at.isoformat(),
                "readCount": notice.read_count,
                "createdBy": {
                    "id": notice.created_by,
                    "name": creator.name if creator else "Unknown",
                    "email": creator.email if creator else ""
                }
            })
            
        return jsonify(notices_data), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@notice_bp.route("", methods=["POST"])
@token_required
@role_required(['academic', 'admin'])
def create_notice(current_user):
    try:
        form_data = request.form
        
        # Get target criteria
        target_department = form_data.get('department')
        target_course = form_data.get('course')
        target_year = form_data.get('year')
        target_section = form_data.get('section')
        
        # Handle recipient emails
        recipient_emails = set()
        manual_emails_str = form_data.get('recipient_emails', '[]')
        manual_emails = json.loads(manual_emails_str)
        for email in manual_emails:
            recipient_emails.add(email.strip())

        # Handle attachments
        attachments = []
        if 'attachments' in request.files:
            for file in request.files.getlist('attachments'):
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    attachments.append(filename)

        # Create notice
        notice = Notice(
            title=form_data.get('title'),
            subject=form_data.get('subject', ''),
            content=form_data.get('content'),
            notice_type=form_data.get('noticeType', ''),
            departments=[target_department] if target_department else [],
            program_course=target_course,
            year=target_year,
            section=target_section,
            recipient_emails=list(recipient_emails),
            priority=form_data.get('priority', 'Normal'),
            send_options=json.loads(form_data.get('send_options', '{"email": false, "web": true}')),
            status=form_data.get('status', 'draft'),
            created_by=str(current_user.id),
            attachments=attachments
        ).save()

        # Get selected students from form
        target_students = json.loads(form_data.get('target_students', '[]'))
        
        # Add notice to selected students
        for student_id in target_students:
            student = Student.objects(id=student_id).first()
            if student:
                student.update(push__notices=notice)
                if student.official_email:
                    recipient_emails.add(student.official_email)

        # Also add notice to students matching the general criteria
        if target_course and target_department:
            student_query = {
                'course': target_course,
                'branch': target_department
            }
            if target_year:
                student_query['year'] = target_year
            if target_section:
                student_query['section'] = target_section
                
            matching_students = Student.objects(**student_query)
            for student in matching_students:
                if str(student.id) not in target_students:  # Don't duplicate if already selected
                    student.update(push__notices=notice)
                    if student.official_email:
                        recipient_emails.add(student.official_email)

        # Update recipient emails in notice if new ones were added
        notice.update(set__recipient_emails=list(recipient_emails))

        # Send emails if needed
        if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
            send_bulk_email(
                recipient_emails=notice.recipient_emails,
                subject=notice.subject or notice.title,
                body=notice.content
            )
        
        return jsonify({
            "message": "Notice created and distributed successfully",
            "noticeId": str(notice.id),
            "recipientCount": len(recipient_emails),
            "studentTargetCount": Student.objects(notices=notice).count()
        }), 201
        
    except Exception as e:
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
        
        # Prepare response data
        notices_data = []
        for notice in notices:
            creator = creators.get(notice.created_by)
            notices_data.append({
                "id": str(notice.id),
                "title": notice.title,
                "content": notice.content,
                "notice_type": notice.notice_type,
                "priority": notice.priority.lower(),
                "createdAt": notice.created_at.isoformat(),
                "attachments": notice.attachments or [],
                "createdBy": {
                    "id": notice.created_by,
                    "name": creator.name if creator else "Unknown",
                    "email": creator.email if creator else ""
                },
                "departments": notice.departments,
                "programCourse": notice.program_course,
                "year": notice.year,
                "section": notice.section,
                "status": notice.status
            })
        
        return jsonify(notices_data), 200
        
    except Exception as e:
        print(f"Error in get_my_notices: {str(e)}")
        return jsonify({"error": "Failed to fetch notices", "details": str(e)}), 500
    

@notice_bp.route("/<notice_id>", methods=["GET"])
@token_required
def get_notice(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404
        
        creator = User.objects(id=ObjectId(notice.created_by)).first()
        
        return jsonify({
            "id": str(notice.id),
            "title": notice.title,
            "subject": notice.subject,
            "content": notice.content,
            "notice_type": notice.notice_type,
            "departments": notice.departments,
            "programCourse": notice.program_course,
            "specialization": notice.specialization,
            "year": notice.year,
            "section": notice.section,
            "recipientEmails": notice.recipient_emails,
            "priority": notice.priority,
            "status": notice.status,
            "sendOptions": notice.send_options,
            "publishAt": notice.publish_at.isoformat() if notice.publish_at else None,
            "createdAt": notice.created_at.isoformat(),
            "updatedAt": notice.updated_at.isoformat(),
            "readCount": notice.read_count,
            "createdBy": {
                "id": notice.created_by,
                "name": creator.name if creator else "Unknown",
                "email": creator.email if creator else ""
            },
            "attachments": notice.attachments
        }), 200
        
    except Exception as e:
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
        if 'attachments' in request.files:
            for file in request.files.getlist('attachments'):
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    notice.attachments.append(filename)

        notice.updated_at = datetime.datetime.now()
        notice.save()
        
        # Send email if the notice is published and has recipients
        if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
            send_bulk_email(
                recipient_emails=notice.recipient_emails,
                subject=notice.subject or notice.title,
                body=notice.content
            )
        
        return jsonify({"message": "Notice updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/<notice_id>", methods=["DELETE"])
@token_required
@role_required(['academic'])
def delete_notice(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice is not there"}), 404
            
        notice.delete()
        return jsonify({"message": "Notice deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/<notice_id>/read", methods=["POST"])
@token_required
def mark_notice_read(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        user_id = str(current_user.id)
        now = datetime.datetime.utcnow()

        # Check if user already read this notice
        existing_read = next((read for read in notice.reads if read.get('user_id') == user_id), None)

        if existing_read:
            # Update existing read timestamp
            notice.update(
                pull__reads={"user_id": user_id}
            )
            notice.update(
                push__reads={
                    "user_id": user_id,
                    "timestamp": now,
                    "is_first_read": False
                }
            )
            return jsonify({
                "message": "Read timestamp updated",
                "isNewRead": False
            }), 200
        else:
            # Add new read record
            notice.update(
                push__reads={
                    "user_id": user_id,
                    "timestamp": now,
                    "is_first_read": True
                }
            )
            # Increment unique read count
            notice.update(inc__read_count=1)
            return jsonify({
                "message": "First read recorded",
                "isNewRead": True
            }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/<notice_id>/reads", methods=["GET"])
@token_required
def get_notice_reads(current_user, notice_id):
    try:
        notice = Notice.objects(id=ObjectId(notice_id)).first()
        if not notice:
            return jsonify({"error": "Notice not found"}), 404

        # Get all unique user IDs who read the notice
        user_ids = list({read['user_id'] for read in notice.reads})
        
        # Get both Users and Students in bulk
        users = User.objects(id__in=user_ids)
        students = Student.objects(id__in=user_ids)
        
        # Create mappings for quick lookup
        user_map = {str(user.id): user for user in users}
        student_map = {str(student.id): student for student in students}
        
        # Count reads per user
        read_counts = {}
        for read in notice.reads:
            user_id = read['user_id']
            read_counts[user_id] = read_counts.get(user_id, 0) + 1

        reads_data = []
        for user_id, count in read_counts.items():
            user = user_map.get(user_id)
            student = student_map.get(user_id)
            
            reads_data.append({
                "user_id": user_id,
                "user_name": user.name if user else "Unknown",
                "user_email": user.email if user else "",
                "roll_number": student.univ_roll_no if student else "null",
                "department": student.branch if student else "null",
                "course": student.course if student else "null",
                "section": student.section if student else "null",
                "read_count": count,
                "last_read": max(
                    [read['timestamp'] for read in notice.reads if read['user_id'] == user_id]
                ).isoformat() if notice.reads else None
            })

        return jsonify({
            "notice_title": notice.title,
            "total_reads": len(notice.reads),
            "unique_readers": notice.read_count,
            "reads": reads_data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@notice_bp.route("/<notice_id>/analytics", methods=["GET"])
@token_required
# @role_required(['academic'])
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
            "attachmentsCount": len(notice.attachments) if notice.attachments else 0
        }
        
        return jsonify(analytics_data), 200
    except Exception as e:
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
        }), 200
        
    except Exception as e:
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
        return jsonify({
            "error": "Failed to fetch notices",
            "details": str(e)
        }), 500