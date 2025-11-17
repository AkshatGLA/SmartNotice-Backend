# from flask import Flask, request, jsonify
# from flask_cors import CORS
# from mongoengine import connect, Document, EmbeddedDocument, EmbeddedDocumentField, StringField, DictField, ListField, DateTimeField, EmailField, IntField, BooleanField
# # from mongoengine import connect, Document, StringField, DictField, ListField, DateTimeField, EmailField, IntField,BooleanField
# from pymongo.errors import ConnectionFailure
# import os
# from dotenv import load_dotenv
# import traceback
# from bson import ObjectId
# from werkzeug.security import generate_password_hash, check_password_hash
# import jwt
# import datetime
# from functools import wraps
# import re
# import json
# from werkzeug.utils import secure_filename,send_file
# import pandas as pd
# import random
# import string

# # /// models 
# from models.notice_model import Notice
# from models.user_model import User
# from models.course_model import Course
# from models.department_model import Department
# from models.student_model import Student

# from io import BytesIO
# from datetime import timedelta
# # Add this import near the top with your other imports
# from utils.email_send_function import send_bulk_email
# load_dotenv()

# app = Flask(__name__)

# CORS(app, resources={
#     r"/api/*": {
#         "origins": ["http://localhost:3000","*"],  # Adjust for your frontend URL
#         "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
#         "allow_headers": ["Authorization", "Content-Type"],
#         "supports_credentials": True
#     }
# })

# # CORS(app)

# app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6k')

# # Database Connection
# MONGO_URI = os.environ.get('MONGO_URI')

# try:
#     connect(
#         db="smart-notice",
#         host=MONGO_URI
#     )
#     print("✅ MongoDB Connected Successfully!")
# except ConnectionFailure as e:
#     print("❌ MongoDB Connection Failed:", str(e))



# def role_required(roles):
#     def decorator(f):
#         @wraps(f)
#         def decorated(current_user, *args, **kwargs):
#             if current_user.role not in roles:
#                 return jsonify({'message': 'Unauthorized access!'}), 403
#             return f(current_user, *args, **kwargs)
#         return decorated
#     return decorator

# # Auth Middleware
# def token_required(f):
#     @wraps(f)
#     def decorated(*args, **kwargs):
#         token = None
        
#         # More flexible header parsing
#         auth_header = request.headers.get('Authorization', '')
#         if auth_header:
#             parts = auth_header.split()
#             if len(parts) == 2 and parts[0].lower() == 'bearer':
#                 token = parts[1]
        
#         if not token:
#             return jsonify({'message': 'Token is missing or malformed!'}), 401
            
#         try:
#             data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
#             current_user = User.objects(id=ObjectId(data['user_id'])).first()
#             if not current_user:
#                 return jsonify({'message': 'User not found!'}), 401
#         except jwt.ExpiredSignatureError:
#             return jsonify({'message': 'Token has expired!'}), 401
#         except Exception as e:
#             print(f"Token validation error: {str(e)}")
#             return jsonify({'message': 'Token is invalid!'}), 401
            
#         return f(current_user, *args, **kwargs)
        
#     return decorated
# # Routes
# @app.route("/")
# def hello():
#     return "Smart Notice API - Ready for development"

# # Auth Routes
# @app.route("/api/auth/signup", methods=["POST"])
# def signup():
#     try:
#         data = request.json
        
#         if User.objects(email=data['email']).first():
#             return jsonify({"error": "Email already exists"}), 400
            
#         hashed_password = generate_password_hash(data['password'])
        
#         user = User(
#             name=data['name'],
#             email=data['email'],
#             password=hashed_password
#         )
#         user.save()
        
#         return jsonify({"message": "User created successfully"}), 201
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500
    

# @app.route("/api/auth/refresh", methods=["POST"])
# def refresh():
#     try:
#         refresh_token = request.json.get('refreshToken')
#         if not refresh_token:
#             return jsonify({"error": "Refresh token required"}), 400
            
#         data = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=["HS256"])
#         user = User.objects(id=ObjectId(data['user_id'])).first()
        
#         if not user:
#             return jsonify({"error": "Invalid user"}), 401
            
#         new_access_token = jwt.encode({
#             'user_id': str(user.id),
#             'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
#         }, app.config['SECRET_KEY'])
        
#         return jsonify({
#             "accessToken": new_access_token,
#             "user": {
#                 "id": str(user.id),
#                 "name": user.name,
#                 "email": user.email,
#                 "role": user.role
#             }
#         }), 200
        
#     except jwt.ExpiredSignatureError:
#         return jsonify({"error": "Refresh token expired"}), 401
#     except Exception as e:
#         print(f"Refresh error: {str(e)}")
#         return jsonify({"error": "Token refresh failed"}), 400


# @app.route("/api/auth/login", methods=["POST"])
# def login():
#     try:
#         data = request.json
#         user = User.objects(email=data['email']).first()
        
#         if not user or not check_password_hash(user.password, data['password']):
#             return jsonify({"error": "Invalid credentials"}), 401
            
#         # Generate both access and refresh tokens
#         access_token = jwt.encode({
#             'user_id': str(user.id),
#             'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)  # Shorter lifespan
#         }, app.config['SECRET_KEY'])
        
#         refresh_token = jwt.encode({
#             'user_id': str(user.id),
#             'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)  # Longer lifespan
#         }, app.config['SECRET_KEY'])
        
#         return jsonify({
#             "accessToken": access_token,
#             "refreshToken": refresh_token,
#             "user": {
#                 "id": str(user.id),
#                 "name": user.name,
#                 "email": user.email,
#                 "role": user.role
#             }
#         }), 200
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

# # Get All Notices - Updated
# @app.route("/api/notices", methods=["GET"])
# @token_required
# @role_required(['admin','user'])
# def get_notices(current_user):
#     try:
#         notices = Notice.objects().order_by('-created_at')
#         user_map = {str(user.id): user for user in User.objects.only('id', 'name', 'email')}
        
#         notices_data = []
#         for notice in notices:
#             creator = user_map.get(notice.created_by)
#             notices_data.append({
#                 "id": str(notice.id),
#                 "title": notice.title,
#                 "subject": notice.subject,
#                 "content": notice.content,  # HTML from RTE
#                 "noticeType": notice.notice_type,
#                 "departments": notice.departments,
#                 "programCourse": notice.program_course,
#                 "specialization": notice.specialization,
#                 "year": notice.year,
#                 "section": notice.section,
#                 "priority": notice.priority,
#                 "status": notice.status,
#                 "publishAt": notice.publish_at.isoformat() if notice.publish_at else None,
#                 "createdAt": notice.created_at.isoformat(),
#                 "readCount": notice.read_count,
#                 "createdBy": {
#                     "id": notice.created_by,
#                     "name": creator.name if creator else "Unknown",
#                     "email": creator.email if creator else ""
#                 }
#             })
            
#         return jsonify(notices_data), 200
        
#     except Exception as e:
#         print(f"Error fetching notices: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# # Add these new routes to app.py

# @app.route('/api/years', methods=['GET'])
# @token_required
# def get_years(current_user):
#     try:
#         # Get a distinct list of all 'year' values from the Student collection
#         years = Student.objects.distinct('year')
#         # Filter out any empty or null values and sort them
#         sorted_years = sorted([y for y in years if y])
#         return jsonify(sorted_years), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/sections', methods=['GET'])
# @token_required
# def get_sections(current_user):
#     try:
#         # Get a distinct list of all 'section' values
#         sections = Student.objects.distinct('section')
#         sorted_sections = sorted([s for s in sections if s])
#         return jsonify(sorted_sections), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
# # @app.route("/api/notices", methods=["POST"])
# # @token_required
# # @role_required(['admin'])
# # def create_notice(current_user):
# #     try:
# #         # Handle form data with file uploads
# #         form_data = request.form
        
# #         # Get file attachments
# #         attachments = []
# #         if 'attachments' in request.files:
# #             for file in request.files.getlist('attachments'):
# #                 if file.filename != '':
# #                     # In a real app, save files to storage (S3, local, etc.)
# #                     filename = secure_filename(file.filename)
# #                     attachments.append(filename)
# #                     # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# #         notice = Notice(
# #             title=form_data.get('title'),
# #             subject=form_data.get('subject', ''),
# #             content=form_data.get('content'),
# #             notice_type=form_data.get('noticeType', ''),
# #             departments=json.loads(form_data.get('departments', '[]')),
# #             program_course=form_data.get('programCourse', ''),
# #             specialization=form_data.get('specialization', 'core'),
# #             year=form_data.get('year', ''),
# #             section=form_data.get('section', ''),
# #             recipient_emails=json.loads(form_data.get('recipient_emails', '[]')),
# #             priority=form_data.get('priority', 'Normal'),
# #             send_options=json.loads(form_data.get('send_options', '{"email": false, "web": true}')),
# #             schedule_date=form_data.get('schedule_date', 'false').lower() == 'true',
# #             schedule_time=form_data.get('schedule_time', 'false').lower() == 'true',
# #             date=form_data.get('date', ''),
# #             time=form_data.get('time', ''),
# #             from_field=form_data.get('from', ''),
# #             status=form_data.get('status', 'draft'),
# #             created_by=str(current_user.id),
# #             attachments=attachments
# #         )

# #         # Handle scheduling
# #         if notice.schedule_date and notice.date:
# #             if notice.schedule_time and notice.time:
# #                 # Combine date and time
# #                 datetime_str = f"{notice.date} {notice.time}"
# #                 notice.publish_at = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
# #             else:
# #                 notice.publish_at = datetime.datetime.strptime(notice.date, '%Y-%m-%d')
            
# #             if notice.publish_at > datetime.datetime.now():
# #                 notice.status = 'scheduled'

# #         notice.save()
# #         # Send email if the notice is published with email option enabled
# #         if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
# #             print(f"Attempting to send email for notice: {notice.title}")
# #             send_bulk_email(
# #                 recipient_emails=notice.recipient_emails,
# #                 subject=notice.subject or notice.title,  # Use title if subject is empty
# #                 body=notice.content
# #             )
# #         # --- END OF ADDED CODE BLOCK ---


# #     except Exception as e:
# #         traceback.print_exc()
# #         return jsonify({"error": str(e)}), 500
# #         # In a real app, you would:
# #         # 1. Send emails if send_options.email is True
# #         # 2. Schedule tasks for future publishing if status is 'scheduled'
        
# #         return jsonify({
# #             "message": "Notice created successfully",
# #             "noticeId": str(notice.id)
# #         }), 201
        
# #     except Exception as e:
# #         traceback.print_exc()
# #         return jsonify({"error": str(e)}), 500


# @app.route("/api/notices", methods=["POST"])
# @token_required
# @role_required(['admin'])
# def create_notice(current_user):
#     try:
#         form_data = request.form
        
#         # --- NEW LOGIC TO FIND STUDENT EMAILS ---
#         target_department = form_data.get('department')
#         target_course = form_data.get('course')
#         target_year = form_data.get('year')
#         target_section = form_data.get('section')
        
#         recipient_emails = set() # Use a set to avoid duplicate emails
        
#         # Add manually entered emails first
#         manual_emails_str = form_data.get('recipient_emails', '[]')
#         manual_emails = json.loads(manual_emails_str)
#         for email in manual_emails:
#             recipient_emails.add(email.strip())

#         # Query the database for students matching the criteria
#         if target_department and target_course and target_year and target_section:
#             query_params = {
#                 'branch': target_department,
#                 'course': target_course,
#                 'year': target_year,
#                 'section': target_section
#             }
#             print(f"Querying students with: {query_params}")
#             matching_students = Student.objects(**query_params)
            
#             student_emails = [s.official_email for s in matching_students if s.official_email]
#             print(f"Found {len(student_emails)} matching student emails.")
#             for email in student_emails:
#                 recipient_emails.add(email)

#         # --- END OF NEW LOGIC ---

#         attachments = []
#         if 'attachments' in request.files:
#             for file in request.files.getlist('attachments'):
#                 if file.filename != '':
#                     filename = secure_filename(file.filename)
#                     attachments.append(filename)

#         notice = Notice(
#             title=form_data.get('title'),
#             subject=form_data.get('subject', ''),
#             content=form_data.get('content'),
#             notice_type=form_data.get('noticeType', ''),
#             # Store the single department for record-keeping
#             departments=[target_department] if target_department else [], 
#             program_course=target_course,
#             year=target_year,
#             section=target_section,
#             recipient_emails=list(recipient_emails), # Save the combined list of emails
#             priority=form_data.get('priority', 'Normal'),
#             send_options=json.loads(form_data.get('send_options', '{"email": false, "web": true}')),
#             status=form_data.get('status', 'draft'),
#             created_by=str(current_user.id),
#             attachments=attachments
#             # Other fields like scheduling can be added back here if needed
#         )

#         notice.save()
        
#         # Send email if the notice is published, has email option, and has recipients
#         if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
#             print(f"Attempting to send email for notice: {notice.title}")
#             send_bulk_email(
#                 recipient_emails=notice.recipient_emails,
#                 subject=notice.subject or notice.title,
#                 body=notice.content
#             )
        
#         return jsonify({
#             "message": "Notice created successfully",
#             "noticeId": str(notice.id)
#         }), 201
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500
# # @app.route("/api/notices/<notice_id>/read", methods=["POST"])
# # @token_required
# # # @role_required(['admin'])
# # def mark_as_read(current_user, notice_id):
# #     try:
# #         user_data = {
# #             "userId": str(current_user.id),
# #             "readAt": datetime.datetime.utcnow().isoformat()
# #         }
        
# #         Notice.objects(id=ObjectId(notice_id)).update_one(
# #             push__readBy=user_data
# #         )
# #         return jsonify({"message": "Marked as read"}), 200
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500


# # Add these new API routes to app.py

# @app.route('/api/departments', methods=['GET'])
# @token_required
# def get_departments(current_user):
#     try:
#         departments = Department.objects.only('name', 'code').order_by('name')
#         return jsonify([{"name": d.name, "code": d.code} for d in departments]), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route('/api/departments/<code>/courses', methods=['GET'])
# @token_required
# def get_courses_by_department(current_user, code):
#     try:
#         department = Department.objects(code=code).first()
#         if not department:
#             return jsonify({"error": "Department not found."}), 404
        
#         courses = sorted(department.courses, key=lambda c: c.name)
#         return jsonify([{"name": c.name, "code": c.code} for c in courses]), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/api/notices/<notice_id>/read", methods=["POST"])
# @token_required
# def mark_notice_read(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404

#         user_id = str(current_user.id)
#         now = datetime.datetime.utcnow()

#         # Check if user already read this notice
#         existing_read = next((read for read in notice.reads if read.get('user_id') == user_id), None)

#         if existing_read:
#             # Update existing read timestamp
#             notice.update(
#                 pull__reads={"user_id": user_id}
#             )
#             notice.update(
#                 push__reads={
#                     "user_id": user_id,
#                     "timestamp": now,
#                     "is_first_read": False
#                 }
#             )
#             return jsonify({
#                 "message": "Read timestamp updated",
#                 "isNewRead": False
#             }), 200
#         else:
#             # Add new read record
#             notice.update(
#                 push__reads={
#                     "user_id": user_id,
#                     "timestamp": now,
#                     "is_first_read": True
#                 }
#             )
#             # Increment unique read count
#             notice.update(inc__read_count=1)
#             return jsonify({
#                 "message": "First read recorded",
#                 "isNewRead": True
#             }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/api/notices/<notice_id>/reads", methods=["GET"])
# @token_required
# @role_required(['admin'])
# def get_notice_reads(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404

#         # Get user details for each read
#         user_ids = list({read['user_id'] for read in notice.reads})  # Get unique user IDs
#         users = User.objects(id__in=user_ids)
#         user_map = {str(user.id): user for user in users}

#         # Count reads per user
#         read_counts = {}
#         for read in notice.reads:
#             user_id = read['user_id']
#             read_counts[user_id] = read_counts.get(user_id, 0) + 1

#         reads_data = []
#         for user_id, count in read_counts.items():
#             user = user_map.get(user_id)
#             reads_data.append({
#                 "user_id": user_id,
#                 "user_name": user.name if user else "Unknown",
#                 "user_email": user.email if user else "",
#                 "roll_number": getattr(user, 'roll_number', 'null'),  # Add if available
#                 "department": getattr(user, 'department', 'null'),    # Add if available
#                 "course": getattr(user, 'course', 'null'),            # Add if available
#                 "section": getattr(user, 'section', 'null'),          # Add if available
#                 "read_count": count,
#                 "last_read": max(
#                     [read['timestamp'] for read in notice.reads if read['user_id'] == user_id]
#                 ).isoformat() if notice.reads else None
#             })

#         return jsonify({
#             "total_reads": len(notice.reads),
#             "unique_readers": notice.read_count,
#             "reads": reads_data
#         }), 200

#     except Exception as e:
#         return jsonify({"error": str(e)}), 500



# @app.route("/api/notices/<notice_id>/analytics", methods=["GET"])
# @token_required
# @role_required(['admin'])
# def get_notice_analytics(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
            
#         # Basic analytics based on available fields
#         analytics_data = {
#             "recipientCount": len(notice.recipient_emails) if notice.recipient_emails else 0,
#             "priority": notice.priority,
#             "status": notice.status,
#             "publishedAt": notice.publishAt.isoformat() if notice.publishAt else None,
#             "createdAt": notice.createdAt.isoformat(),
#             "attachmentsCount": len(notice.attachments) if notice.attachments else 0
#         }
        
#         # If you want to add read tracking later, you can add this field to your schema
#         # and then include: "readCount": len(notice.readBy) if hasattr(notice, 'readBy') else 0
        
#         return jsonify(analytics_data), 200
#     except Exception as e:
#         print(f"Analytics error: {str(e)}")
#         return jsonify({"error": "Failed to fetch analytics"}), 500



# @app.route("/api/notices/<notice_id>", methods=["GET"])
# @token_required
# def get_notice(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found"}), 404
        
#         creator = User.objects(id=ObjectId(notice.created_by)).first()
        
#         return jsonify({
#             "id": str(notice.id),
#             "title": notice.title,
#             "subject": notice.subject,
#             "content": notice.content,  # HTML content from RTE
#             "noticeType": notice.notice_type,
#             "departments": notice.departments,
#             "programCourse": notice.program_course,
#             "specialization": notice.specialization,
#             "year": notice.year,
#             "section": notice.section,
#             "recipientEmails": notice.recipient_emails,
#             "priority": notice.priority,
#             "status": notice.status,
#             "sendOptions": notice.send_options,
#             "scheduleDate": notice.schedule_date,
#             "scheduleTime": notice.schedule_time,
#             "date": notice.date,
#             "time": notice.time,
#             "from": notice.from_field,
#             "publishAt": notice.publish_at.isoformat() if notice.publish_at else None,
#             "createdAt": notice.created_at.isoformat(),
#             "updatedAt": notice.updated_at.isoformat(),
#             "readCount": notice.read_count,
#             "createdBy": {
#                 "id": notice.created_by,
#                 "name": creator.name if creator else "Unknown",
#                 "email": creator.email if creator else ""
#             },
#             "attachments": notice.attachments
#         }), 200
        
#     except Exception as e:
#         print(f"Error fetching notice: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# # Similarly update the update_notice endpoint
# # @app.route("/api/notices/<notice_id>", methods=["PUT"])
# # @token_required
# # @role_required(['admin'])
# # def update_notice(current_user, notice_id):
# #     try:
# #         notice = Notice.objects(id=ObjectId(notice_id), created_by=str(current_user.id)).first()
# #         if not notice:
# #             return jsonify({"error": "Notice not found or unauthorized"}), 404
            
# #         form_data = request.form
        
# #         # Update fields
# #         notice.title = form_data.get('title', notice.title)
# #         notice.subject = form_data.get('subject', notice.subject)
# #         notice.content = form_data.get('content', notice.content)
# #         notice.notice_type = form_data.get('notice_type', notice.notice_type)
# #         notice.departments = json.loads(form_data.get('departments', json.dumps(notice.departments)))
# #         notice.program_course = form_data.get('program_course', notice.program_course)
# #         notice.specialization = form_data.get('specialization', notice.specialization)
# #         notice.year = form_data.get('year', notice.year)
# #         notice.section = form_data.get('section', notice.section)
# #         notice.recipient_emails = json.loads(form_data.get('recipient_emails', json.dumps(notice.recipient_emails)))
# #         notice.priority = form_data.get('priority', notice.priority)
# #         notice.send_options = json.loads(form_data.get('send_options', json.dumps(notice.send_options)))
# #         notice.schedule_date = form_data.get('schedule_date', str(notice.schedule_date)).lower() == 'true'
# #         notice.schedule_time = form_data.get('schedule_time', str(notice.schedule_time)).lower() == 'true'
# #         notice.date = form_data.get('date', notice.date)
# #         notice.time = form_data.get('time', notice.time)
# #         notice.from_field = form_data.get('from', notice.from_field)
# #         notice.status = form_data.get('status', notice.status)
        
# #         # Handle file attachments
# #         if 'attachments' in request.files:
# #             for file in request.files.getlist('attachments'):
# #                 if file.filename != '':
# #                     filename = secure_filename(file.filename)
# #                     notice.attachments.append(filename)
# #                     # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

# #         # Update scheduling
# #         if notice.schedule_date and notice.date:
# #             if notice.schedule_time and notice.time:
# #                 datetime_str = f"{notice.date} {notice.time}"
# #                 notice.publish_at = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
# #             else:
# #                 notice.publish_at = datetime.datetime.strptime(notice.date, '%Y-%m-%d')
            
# #             if notice.publish_at > datetime.datetime.now():
# #                 notice.status = 'scheduled'
# #             else:
# #                 notice.status = 'published'

# #         notice.updated_at = datetime.datetime.now()
# #         notice.save()
# #         # --- ADD THIS CODE BLOCK ---
# #         # Send email if the notice is published with email option enabled
# #         if notice.status == 'published' and notice.send_options.get('email') and notice.recipient_emails:
# #             print(f"Attempting to send email for updated notice: {notice.title}")
# #             send_bulk_email(
# #                 recipient_emails=notice.recipient_emails,
# #                 subject=notice.subject or notice.title, # Use title if subject is empty
# #                 body=notice.content
# #             )
# #         # --- END OF ADDED CODE BLOCK ---

        
# #         return jsonify({"message": "Notice updated successfully"}), 200
# #     except Exception as e:
# #         return jsonify({"error": str(e)}), 500
# @app.route("/api/notices/<notice_id>", methods=["PUT"])
# @token_required
# @role_required(['admin'])
# def update_notice(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id), created_by=str(current_user.id)).first()
#         if not notice:
#             return jsonify({"error": "Notice not found or unauthorized"}), 404
            
#         form_data = request.form
        
#         # ... (all your field updates) ...
#         notice.title = form_data.get('title', notice.title)
#         notice.subject = form_data.get('subject', notice.subject)
#         notice.content = form_data.get('content', notice.content)
#         notice.notice_type = form_data.get('notice_type', notice.notice_type)
#         notice.departments = json.loads(form_data.get('departments', json.dumps(notice.departments)))
#         notice.program_course = form_data.get('program_course', notice.program_course)
#         notice.specialization = form_data.get('specialization', notice.specialization)
#         notice.year = form_data.get('year', notice.year)
#         notice.section = form_data.get('section', notice.section)
#         notice.recipient_emails = json.loads(form_data.get('recipient_emails', json.dumps(notice.recipient_emails)))
#         notice.priority = form_data.get('priority', notice.priority)
#         notice.send_options = json.loads(form_data.get('send_options', json.dumps(notice.send_options)))
#         notice.schedule_date = form_data.get('schedule_date', str(notice.schedule_date)).lower() == 'true'
#         notice.schedule_time = form_data.get('schedule_time', str(notice.schedule_time)).lower() == 'true'
#         notice.date = form_data.get('date', notice.date)
#         notice.time = form_data.get('time', notice.time)
#         notice.from_field = form_data.get('from', notice.from_field)
#         notice.status = form_data.get('status', notice.status)

#         # ... (attachment handling) ...

#         # Update scheduling
#         if notice.schedule_date and notice.date:
#             if notice.schedule_time and notice.time:
#                 datetime_str = f"{notice.date} {notice.time}"
#                 notice.publish_at = datetime.datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
#             else:
#                 notice.publish_at = datetime.datetime.strptime(notice.date, '%Y-%m-%d')
            
#             if notice.publish_at > datetime.datetime.now():
#                 notice.status = 'scheduled'
#             else:
#                 notice.status = 'published'

#         notice.updated_at = datetime.datetime.now()
#         notice.save()
        
#         # Send email if the notice is published and has recipients (checkbox is ignored)
#         if notice.status == 'published' and notice.recipient_emails:
#             print(f"Attempting to send email for updated notice: {notice.title}")
#             send_bulk_email(
#                 recipient_emails=notice.recipient_emails,
#                 subject=notice.subject or notice.title,
#                 body=notice.content
#             )

#         return jsonify({"message": "Notice updated successfully"}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
# @app.route("/api/notices/<notice_id>", methods=["DELETE"])
# @token_required
# @role_required(['admin'])
# def delete_notice(current_user, notice_id):
#     try:
#         notice = Notice.objects(id=ObjectId(notice_id), createdBy=str(current_user.id)).first()
        
#         if not notice:
#             return jsonify({"error": "Notice not found or unauthorized"}), 404
            
#         notice.delete()
#         return jsonify({"message": "Notice deleted successfully"}), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    
# @app.route("/api/users", methods=["GET"])
# @token_required
# @role_required(['admin'])
# def get_users(current_user):
#     try:
#         # if current_user.role != "admin":
#             # return jsonify({"error": "Unauthorized"}), 403
                
#         users = User.objects().only('id', 'name', 'email')
#         return jsonify([{
#             "id": str(user.id),
#             "name": user.name,
#             "email": user.email
#         } for user in users]), 200
#     except Exception as e:
#         print(f"Users error: {str(e)}")
#         return jsonify({"error": "Failed to fetch users"}), 500


# @app.route("/api/notices/analytics", methods=["GET"])
# @token_required
# @role_required(['admin'])
# def get_all_notices_analytics(current_user):
#     try:
#         # If you add readBy field to schema
#         total_reads = sum(len(notice.readBy) for notice in Notice.objects())
        
#         # Or if you don't have read tracking
#         total_notices = Notice.objects.count()
        
#         return jsonify({
#             "totalNotices": total_notices,
#             # "totalReads": total_reads,  # Only include if you have readBy field
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500


# @app.route("/api/users/count", methods=["GET"])
# @token_required
# @role_required(['admin'])
# def get_users_count(current_user):
#     try:
#         count = User.objects.count()
#         return jsonify({"count": count}), 200
#     except Exception as e:
#         print(f"Error counting users: {str(e)}")
#         return jsonify({"error": "Failed to count users"}), 500 


# @app.route("/api/auth/current-user", methods=["GET"])
# @token_required
# @role_required(['admin','user'])
# def get_current_user(current_user):
#     try:
#         return jsonify({
#             "id": str(current_user.id),
#             "name": current_user.name,
#             "email": current_user.email,
#             "role": current_user.role
#         }), 200
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/api/auth/logout", methods=["POST"])
# def logout():
#     # In JWT, logout is handled client-side by discarding tokens
#     return jsonify({"message": "Logged out successfully"}), 200


# @app.route("/api/notices/created-by/<user_id>", methods=["GET"])
# @token_required
# def get_notices_by_creator(current_user, user_id):
#     try:
#         # Verify the requesting user has permission
#         if current_user.role != "admin" and str(current_user.id) != user_id:
#             return jsonify({"error": "Unauthorized"}), 403

#         notices = Notice.objects(created_by=user_id).order_by('-created_at')
        
#         user_map = {str(user.id): user for user in User.objects.only('id', 'name', 'email')}
        
#         notices_data = []
#         for notice in notices:
#             creator = user_map.get(notice.created_by)
#             notices_data.append({
#                 "id": str(notice.id),
#                 "title": notice.title,
#                 "content": notice.content,
#                 "notice_type": notice.notice_type,
#                 "departments": notice.departments,
#                 "year": notice.year,
#                 "section": notice.section,
#                 "recipient_emails": notice.recipient_emails,
#                 "priority": notice.priority,
#                 "status": notice.status,
#                 "publish_at": notice.publish_at.isoformat() if notice.publish_at else None,
#                 "created_at": notice.created_at.isoformat(),
#                 "updated_at": notice.updated_at.isoformat(),
#                 "created_by": {
#                     "id": notice.created_by,
#                     "name": creator.name if creator else "Unknown",
#                     "email": creator.email if creator else ""
#                 },
#                 "attachments": notice.attachments
#             })
            
#         return jsonify(notices_data), 200
        
#     except Exception as e:
#         print(f"Error fetching user's notices: {str(e)}")
#         traceback.print_exc()
#         return jsonify({
#             "error": "Failed to fetch notices",
#             "details": str(e)
#         }), 500
    

#     # ///////////////////// Methods to upload Student details ///////////////////////

# # Password generation helper
# def generate_password(length=6):
#     chars = string.ascii_letters + string.digits
#     return ''.join(random.choice(chars) for _ in range(length))

# # Excel date to ISO converter
# def excel_date_to_iso(excel_date):
#     try:
#         return (datetime(1899, 12, 30) + timedelta(days=float(excel_date))).isoformat()
#     except:
#         return None



# # Student login endpoint
# @app.route("/api/students/login", methods=["POST"])
# def student_login():
#     try:
#         data = request.json
#         student = Student.objects(univ_roll_no=data.get('univ_roll_no')).first()
        
#         if not student or not check_password_hash(student.password, data.get('password', '')):
#             return jsonify({"error": "Invalid credentials"}), 401
            
#         # Generate token (similar to your user login)
#         access_token = jwt.encode({
#             'student_id': str(student.id),
#             'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
#         }, app.config['SECRET_KEY'])
        
#         return jsonify({
#             "accessToken": access_token,
#             "student": {
#                 "name": student.name,
#                 "univ_roll_no": student.univ_roll_no,
#                 "course": student.course,
#                 "branch": student.branch
#             }
#         }), 200
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

# # Helper function to find a value in a row using multiple possible column names
# def get_column_value(row, column_map, field_name):
#     for column_name in column_map[field_name]:
#         if column_name in row:
#             return str(row[column_name]).strip()
#     return "" # Return empty string if no matching column is found

# @app.route("/api/students/upload-details", methods=["POST"])
# @token_required
# @role_required(['admin'])
# def upload_student_details(current_user):
#     COLUMN_MAP = {
#         'name': ['name', 'student name', 'student_name'],
#         'univ_roll_no': ['univ_roll_no', 'univ rollno', 'univ. rollno.', 'roll no', 'roll_no'],
#         'class_roll_no': ['class_roll_no', 'class roll no'],
#         'email': ['email', 'email id', 'official_email', 'official email-id'],
#         'father_name': ['fathers name', 'father_name', 'father name'],
#         'student_mobile': ['stu. mob.', 'student_mobile', 'mobile no', 'student contact'],
#         'father_mobile': ['father mob.', 'father_mobile', 'father contact']
#     }

#     try:
#         department = request.form.get('department')
#         course = request.form.get('course')
#         year = request.form.get('year')
#         section = request.form.get('section')
#         file = request.files.get('file')

#         if not all([department, course, year, section, file]):
#             return jsonify({"error": "Missing required form data or file."}), 400

#         print("✅ File received. Attempting to read...")
#         try:
#             if file.filename.lower().endswith('.csv'):
#                 df = pd.read_csv(file, encoding='utf-8', skipinitialspace=True)
#             else:
#                 df = pd.read_excel(file)
#         except Exception as e:
#             print("❌ FAILED TO READ FILE. Error details below:")
#             traceback.print_exc()
#             return jsonify({"error": f"Could not read the file. Please check the format. Details: {str(e)}"}), 400

#         df.columns = [col.strip().lower() for col in df.columns]
#         df = df.fillna('')
#         print(f"✅ File read successfully. Found {len(df)} rows.")

#         students_to_create = []
#         errors = [] # This list will now be for skipped students

#         for index, row in df.iterrows():
#             univ_roll_no = get_column_value(row, COLUMN_MAP, 'univ_roll_no')
#             if not univ_roll_no:
#                 errors.append(f"Row {index + 2}: Skipped. Could not find a University Roll Number.")
#                 continue

#             if Student.objects(univ_roll_no=univ_roll_no).first():
#                 errors.append(f"Row {index + 2}: Skipped. Student with Roll Number '{univ_roll_no}' already exists.")
#                 continue

#             # This part is only reached for NEW students
#             raw_password = generate_password()
#             official_email = get_column_value(row, COLUMN_MAP, 'email')
#             login_email = official_email if official_email else f"{univ_roll_no}@university.edu"
#             student = Student(
#                 branch=department, course=course, year=year, section=section,
#                 univ_roll_no=univ_roll_no,
#                 name=get_column_value(row, COLUMN_MAP, 'name'),
#                 class_roll_no=get_column_value(row, COLUMN_MAP, 'class_roll_no'),
#                 father_name=get_column_value(row, COLUMN_MAP, 'father_name'),
#                 student_mobile=get_column_value(row, COLUMN_MAP, 'student_mobile'),
#                 father_mobile=get_column_value(row, COLUMN_MAP, 'father_mobile'),
#                 official_email=official_email,
#                 email=login_email.lower(),
#                 password=generate_password_hash(raw_password),
#                 raw_password=raw_password
#             )
#             students_to_create.append(student)

#         # --- THIS IS THE KEY LOGIC CHANGE ---
#         # Only insert if there are new students to create.
#         if students_to_create:
#             Student.objects.insert(students_to_create)

#         # Always return a success response, but include the list of skipped students.
#         message = f"Process complete. Successfully created {len(students_to_create)} new students."
#         if not students_to_create and errors:
#              message = "No new students were added."
        
#         return jsonify({
#             "message": message,
#             "errors": errors  # List of skipped students
#         }), 201

#     except Exception as e:
#         print("❌ An unexpected server error occurred:")
#         traceback.print_exc()
#         return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500
    
# # Get students by branch/course (for notice targeting)
# @app.route("/api/students", methods=["GET"])
# @token_required
# def get_students(current_user):
#     try:
#         branch = request.args.get('branch')
#         course = request.args.get('course')
        
#         query = {}
#         if branch:
#             query["branch"] = branch
#         if course:
#             query["course"] = course
            
#         students = Student.objects(**query).only(
#             'email', 'official_email', 'name', 'univ_roll_no', 'course', 'branch'
#         )
        
#         return jsonify([{
#             "email": s.official_email or s.email,
#             "name": s.name,
#             "univ_roll_no": s.univ_roll_no,
#             "course": s.course,
#             "branch": s.branch
#         } for s in students]), 200
        
#     except Exception as e:
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500
    

# from flask import send_file
# import os

# @app.route('/api/students/template')
# @token_required
# def download_student_template(current_user):
#     try:
#         # Path to your template file
#         template_path = os.path.join(os.path.dirname(__file__), 'static', 'templates', 'student_template.xlsx')
        
#         # Verify file exists
#         if not os.path.exists(template_path):
#             return jsonify({"error": "Template file not found"}), 404
            
#         return send_file(
#             template_path,
#             as_attachment=True,
#             download_name="student_data_template.xlsx",
#             mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#         )
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# # Add this one-time seeder route to app.py

# @app.route('/api/setup/seed-departments', methods=['GET'])
# def seed_departments():
#     # Check if data already exists to prevent duplicates
#     if Department.objects.count() > 0:
#         return jsonify({"message": "Departments have already been seeded."}), 400

#     department_data = [
#         {"name": "Computer Engineering & Applications", "code": "CEA", "courses": [
#             {"name": "B.Tech in CSE", "code": "BTECH_CSE"},
#             {"name": "B.Tech (Hons.) CSE (Specialization in AI & Analytics)", "code": "BTECH_HONS_AI"},
#             {"name": "B.Tech CSE (Specialization in AIML)", "code": "BTECH_AIML"},
#             {"name": "B.Tech Lateral Entry – CSE", "code": "BTECH_LAT_CSE"},
#             {"name": "BCA / BCA (Hons./By Research)", "code": "BCA"},
#             {"name": "BCA Data Science", "code": "BCA_DS"},
#             {"name": "BCA in Digital Marketing", "code": "BCA_DM"}
#         ]},
#         {"name": "Electronics & Communication Engineering (ECE)", "code": "ECE", "courses": [
#             {"name": "B.Tech in Electronics and Computer Engineering", "code": "BTECH_ECS"},
#             {"name": "B.Tech EC (Minor in CS)", "code": "BTECH_EC_CS"},
#             {"name": "B.Tech EC (Specialization in VLSI)", "code": "BTECH_EC_VLSI"},
#             {"name": "B.Tech in ECE", "code": "BTECH_ECE"},
#             {"name": "B.Tech Lateral Entry – EC, ECE", "code": "BTECH_LAT_ECE"}
#         ]},
#         {"name": "Electrical Engineering", "code": "EE", "courses": [
#             {"name": "B.Tech in EE", "code": "BTECH_EE"},
#             {"name": "B.Tech in EEE", "code": "BTECH_EEE"},
#             {"name": "B.Tech EE (EV Technology)", "code": "BTECH_EE_EV"},
#             {"name": "B.Tech EE (Minor in CS)", "code": "BTECH_EE_CS"},
#             {"name": "B.Tech Lateral Entry – EE, EEE, EE (EV Technology)", "code": "BTECH_LAT_EE"}
#         ]},
#         {"name": "Mechanical Engineering", "code": "ME", "courses": [
#             {"name": "B.Tech in ME", "code": "BTECH_ME"},
#             {"name": "B.Tech ME (Minor in CS)", "code": "BTECH_ME_CS"},
#             {"name": "B.Tech ME (Automobile)", "code": "BTECH_ME_AUTO"},
#             {"name": "B.Tech ME (Mechatronics)", "code": "BTECH_ME_MECHA"},
#             {"name": "B.Tech Lateral Entry – ME", "code": "BTECH_LAT_ME"},
#             {"name": "ME in Smart Manufacturing", "code": "MTECH_SM"}
#         ]},
#         {"name": "Civil Engineering", "code": "CE", "courses": [
#             {"name": "B.Tech in CE", "code": "BTECH_CE"},
#             {"name": "B.Tech Lateral Entry – CE", "code": "BTECH_LAT_CE"}
#         ]},
#         {"name": "Biotechnology", "code": "BT", "courses": [
#             {"name": "B.Tech in Biotech", "code": "BTECH_BT"},
#             {"name": "B.Tech Lateral Entry – Biotech", "code": "BTECH_LAT_BT"},
#             {"name": "B.Sc. Biotech / B.Sc. Biotech (Hons./By Research)", "code": "BSC_BT"}
#         ]},
#         {"name": "Pharmaceutical Sciences", "code": "PHARM", "courses": [
#             {"name": "B.Pharm", "code": "BPHARM"},
#             {"name": "B.Pharm (Lateral Entry)", "code": "BPHARM_LAT"},
#             {"name": "Pharm.D", "code": "PHARMD"}
#         ]},
#         {"name": "Faculty of Agricultural Sciences", "code": "AGRI", "courses": [
#             {"name": "B.Sc. (Hons.) Agriculture", "code": "BSC_AGRI"}
#         ]},
#         {"name": "Physics / Chemistry / Mathematics", "code": "SCI", "courses": [
#             {"name": "B.Sc. Physics / B.Sc. Physics (Hons./By Research)", "code": "BSC_PHY"},
#             {"name": "B.Sc. Chemistry / B.Sc. Chemistry (Hons./By Research)", "code": "BSC_CHEM"},
#             {"name": "B.Sc. Maths / B.Sc. Maths (Hons./By Research in DS)", "code": "BSC_MATH"}
#         ]},
#         {"name": "Social Science & Humanities / English", "code": "HUM", "courses": [
#             {"name": "B.A. Eng / B.A. Eng (Hons./By Research)", "code": "BA_ENG"},
#             {"name": "B.A. Eco / B.A. Eco (Hons./By Research)", "code": "BA_ECO"}
#         ]},
#         {"name": "Business Management / Commerce", "code": "MGMT", "courses": [
#             {"name": "BBA / BBA (Hons./By Research)", "code": "BBA"},
#             {"name": "BBA (Family Business)", "code": "BBA_FB"},
#             {"name": "BBA (Management Sciences)", "code": "BBA_MS"},
#             {"name": "B.Com / B.Com (Hons./By Research)", "code": "BCOM"},
#             {"name": "B.Com Global Accounting in Association with CIMA", "code": "BCOM_CIMA"}
#         ]},
#         {"name": "Legal Studies", "code": "LAW", "courses": [
#             {"name": "BBA LLB (Hons.)", "code": "BBALLB"},
#             {"name": "B.A. LLB (Hons.)", "code": "BALLB"}
#         ]},
#         {"name": "Faculty of Education", "code": "EDU", "courses": [
#             {"name": "B.Ed.", "code": "BED"}
#         ]},
#         {"name": "Library & Information Science", "code": "LIB", "courses": [
#             {"name": "Bachelor of Library and Information Science", "code": "BLIS"}
#         ]}
#     ]
    
#     try:
#         for dept_info in department_data:
#             courses = [Course(name=c['name'], code=c['code']) for c in dept_info['courses']]
#             department = Department(name=dept_info['name'], code=dept_info['code'], courses=courses)
#             department.save()
#         return jsonify({"message": f"Successfully seeded {len(department_data)} departments."}), 201
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500        


# if __name__ == "__main__":
#     app.run(debug=True, port=5001)




# # from flask import Flask
# # from flask_cors import CORS
# # from pymongo.errors import ConnectionFailure
# # from config import Config
# # from models.user_model import User
# # from models.notice_model import Notice
# # from controllers.auth import init_auth_routes
# # from controllers.notices import init_notice_routes
# # from controllers.user import init_user_routes
# # from mongoengine import connect

# # def create_app():
# #     app = Flask(__name__)
# #     app.config.from_object(Config)
    
# #     # Initialize CORS
# #     CORS(app, resources={
# #         r"/api/*": {
# #             "origins": ["http://localhost:5173"],
# #             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
# #             "allow_headers": ["Authorization", "Content-Type"],
# #             "supports_credentials": True
# #         }
# #     })
    
# #     # Connect to MongoDB
# #     try:
# #         connect(
# #             db="smart-notice",
# #             host=app.config['MONGO_URI']
# #         )
# #         print("✅ MongoDB Connected Successfully!")
# #     except ConnectionFailure as e:
# #         print("❌ MongoDB Connection Failed:", str(e))
    
# #     # Initialize routes
# #     init_auth_routes(app)
# #     init_notice_routes(app)
# #     init_user_routes(app)
    
# #     @app.route("/")
# #     def hello():
# #         return "Smart Notice API - Ready for development"
    
# #     return app

# # if __name__ == "__main__":
# #     app = create_app()
# #     app.run(debug=True, port=5001)






