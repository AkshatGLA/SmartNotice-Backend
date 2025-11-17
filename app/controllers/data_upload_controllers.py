# ===============================================================
# Controller for Data Upload Functionality (With Socket.IO Integration)
# File: app/controllers/data_upload_controller.py
# ===============================================================

from flask import Blueprint, request, jsonify, current_app
from mongoengine import Document, StringField, EmailField, DateTimeField
import pandas as pd
import random
import string
import traceback
import datetime
from functools import wraps
import jwt
from bson import ObjectId
from werkzeug.security import generate_password_hash

# Import models and middleware
from ..models.student_model import Student
from ..models.employee_model import Employee
from ..models.course_model import Course
from ..models.department_model import Department
from ..middleware.auth_middleware import token_required, role_required

# Import socketio from extensions
from app.extensions import socketio

# --- Helper Functions ---

def generate_password(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_column_value(row, column_map, field_name):
    for column_name in column_map.get(field_name, []):
        if column_name in row:
            return str(row[column_name]).strip()
    return ""

# --- Helper function for safe socket emission ---
def safe_socket_emit(event_name, data):
    """Safely emit socket events with error handling"""
    try:
        if socketio:
            socketio.emit(event_name, data, namespace='/')
            current_app.logger.info(f"Emitted socket event: {event_name}")
        else:
            current_app.logger.warning(f"SocketIO not initialized, skipping event: {event_name}")
    except Exception as e:
        current_app.logger.error(f"Error emitting socket event {event_name}: {str(e)}")

# --- Blueprint Definition ---
data_upload_bp = Blueprint('data_upload_api', __name__, url_prefix="/api")

# --- API Routes ---

@data_upload_bp.route('/departments', methods=['GET'])
@token_required
def get_departments(current_user):
    try:
        departments = Department.objects.only('name', 'code').order_by('name')
        return jsonify([{"name": d.name, "code": d.code} for d in departments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_upload_bp.route('/departments/<code>/courses', methods=['GET'])
@token_required
def get_courses_by_department(current_user, code):
    try:
        department = Department.objects(code=code).first()
        if not department:
            return jsonify({"error": "Department not found."}), 404
        courses = sorted(department.courses, key=lambda c: c.name)
        return jsonify([{"name": c.name, "code": c.code} for c in courses]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@data_upload_bp.route("/students/upload-details", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def upload_student_details(current_user):
    COLUMN_MAP = {
        'name': ['name', 'student name', 'student_name', 'full name'],
        'univ_roll_no': ['univ_roll_no', 'univ rollno', 'roll no', 'roll_no', 'university roll no'],
        'email': ['email', 'email id', 'official_email', 'official email id'],
        'father_name': ['fathers name', 'father_name', "father's name"],
        'student_mobile': ['stu. mob.', 'student_mobile', 'mobile no', 'student mobile'],
        'father_mobile': ['father mob.', 'father_mobile', "father's mobile"]
    }
    try:
        department = request.form.get('department')
        course = request.form.get('course')
        year = request.form.get('year')
        section = request.form.get('section')
        file = request.files.get('file')

        if not all([department, course, year, section, file]):
            return jsonify({"error": "Missing required form data or file."}), 400

        df = pd.read_excel(file) if file.filename.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        df.columns = [str(col).strip().lower() for col in df.columns]
        df = df.fillna('')

        # Debugging and Improved Error Handling
        current_app.logger.info(f"Detected column headers in file: {list(df.columns)}")

        # Check if the essential roll number column exists
        roll_no_found = any(col in df.columns for col in COLUMN_MAP['univ_roll_no'])
        if not roll_no_found:
            error_msg = (
                "Upload failed: Could not find the 'University Roll Number' column. "
                f"Please make sure your file has a column named one of the following: {', '.join(COLUMN_MAP['univ_roll_no'])}. "
                f"The headers we actually found were: {', '.join(list(df.columns))}"
            )
            return jsonify({"error": error_msg}), 400

        students_to_create = []
        conflicts = []
        errors = []

        for index, row in df.iterrows():
            univ_roll_no = get_column_value(row, COLUMN_MAP, 'univ_roll_no')
            if not univ_roll_no:
                errors.append(f"Row {index + 2}: Skipped. Missing University Roll Number.")
                continue

            if Student.objects(univ_roll_no=univ_roll_no).first():
                conflicts.append(f"Student with roll number '{univ_roll_no}' already exists.")
                continue

            raw_password = generate_password()
            official_email = get_column_value(row, COLUMN_MAP, 'email')
            login_email = official_email if official_email else f"{univ_roll_no}@university.edu"
            
            # Hash the password before saving
            hashed_password = generate_password_hash(raw_password)
            
            student = Student(
                branch=department, course=course, year=year, section=section,
                univ_roll_no=univ_roll_no,
                name=get_column_value(row, COLUMN_MAP, 'name'),
                father_name=get_column_value(row, COLUMN_MAP, 'father_name'),
                student_mobile=get_column_value(row, COLUMN_MAP, 'student_mobile'),
                father_mobile=get_column_value(row, COLUMN_MAP, 'father_mobile'),
                official_email=official_email,
                email=login_email.lower(),
                password=hashed_password,  # Save hashed password
                raw_password=raw_password  # Store raw password for reference only
            )
            students_to_create.append(student)

        if students_to_create:
            Student.objects.insert(students_to_create)
            # Emit socket event for real-time updates using safe function
            safe_socket_emit('students_uploaded', {
                'count': len(students_to_create),
                'uploader': current_user.name,
                'department': department,
                'course': course
            })

        message = f"Successfully created {len(students_to_create)} new students."
        if conflicts:
            message += f" {len(conflicts)} students already existed and were skipped."
        if errors:
            message += f" Encountered {len(errors)} errors."

        return jsonify({
            "message": message,
            "created_count": len(students_to_create),
            "conflicts": conflicts,
            "errors": errors
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error in upload_student_details: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@data_upload_bp.route("/students/add-manual", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def add_student_manual(current_user):
    try:
        data = request.json
        univ_roll_no = data.get('univ_roll_no')
        
        if Student.objects(univ_roll_no=univ_roll_no).first():
            existing_student = Student.objects.get(univ_roll_no=univ_roll_no)
            return jsonify({
                "error": f"Student with Roll Number '{univ_roll_no}' already exists.",
                "existing_data": existing_student.to_profile_dict()
            }), 409

        raw_password = generate_password()
        # Hash the password before saving
        hashed_password = generate_password_hash(raw_password)
        
        student = Student(
            branch=data.get('department'),
            course=data.get('course'),
            year=data.get('year'),
            section=data.get('section'),
            name=data.get('name'),
            univ_roll_no=univ_roll_no,
            student_mobile=data.get('student_mobile'),
            father_name=data.get('father_name'),
            father_mobile=data.get('father_mobile'),
            official_email=data.get('official_email', '').lower(),
            email=data.get('official_email', '').lower(),
            password=hashed_password,  # Save hashed password
            raw_password=raw_password  # Store raw password for reference only
        )
        student.save()
        
        # Emit socket event for real-time updates using safe function
        safe_socket_emit('student_added', {
            'id': str(student.id),
            'name': student.name,
            'roll_no': student.univ_roll_no,
            'uploader': current_user.name
        })
        
        return jsonify({"message": f"Successfully created student '{data.get('name')}'."}), 201
    except Exception as e:
        current_app.logger.error(f"Error in add_student_manual: {str(e)}")
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/students/update-manual/<univ_roll_no>", methods=["PUT"])
@token_required
@role_required(['admin', 'academic'])
def update_student_manual(current_user, univ_roll_no):
    try:
        data = request.json
        student = Student.objects(univ_roll_no=univ_roll_no).first()
        if not student:
            return jsonify({"error": "Student not found."}), 404
        
        student.branch = data.get('department', student.branch)
        student.course = data.get('course', student.course)
        student.year = data.get('year', student.year)
        student.section = data.get('section', student.section)
        student.name = data.get('name', student.name)
        student.student_mobile = data.get('student_mobile', student.student_mobile)
        student.father_name = data.get('father_name', student.father_name)
        student.father_mobile = data.get('father_mobile', student.father_mobile)
        student.official_email = data.get('official_email', student.official_email).lower()
        student.email = data.get('official_email', student.email).lower()
        
        student.save()
        
        # Emit socket event for real-time updates using safe function
        safe_socket_emit('student_updated', {
            'id': str(student.id),
            'name': student.name,
            'roll_no': student.univ_roll_no,
            'updater': current_user.name
        })
        
        return jsonify({"message": f"Successfully updated student '{student.name}'."}), 200
    except Exception as e:
        current_app.logger.error(f"Error in update_student_manual: {str(e)}")
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/teachers/upload-details", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def upload_teacher_details(current_user):
    COLUMN_MAP = {
        'employee_id': ['employee id', 'employee_id', 'emp_id', 'employee number'],
        'name': ['name', 'teacher name', 'teacher_name', 'full name'],
        'post': ['post', 'designation'],
        'mobile': ['mobile', 'contact no', 'phone', 'mobile number'],
        'official_email': ['email', 'official email', 'official_email', 'email id']
    }
    try:
        department = request.form.get('department')
        file = request.files.get('file')

        if not all([department, file]):
            return jsonify({"error": "Department and file are required."}), 400

        df = pd.read_excel(file) if file.filename.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        df.columns = [str(col).strip().lower() for col in df.columns]
        df = df.fillna('')

        teachers_to_create = []
        conflicts = []
        errors = []

        for index, row in df.iterrows():
            employee_id = get_column_value(row, COLUMN_MAP, 'employee_id')
            if not employee_id:
                errors.append(f"Row {index + 2}: Skipped. Missing Employee ID.")
                continue

            if Employee.objects(employee_id=employee_id).first():
                conflict_data = {
                    'employee_id': employee_id,
                    'name': get_column_value(row, COLUMN_MAP, 'name'),
                    'post': get_column_value(row, COLUMN_MAP, 'post'),
                    'mobile': get_column_value(row, COLUMN_MAP, 'mobile'),
                    'official_email': get_column_value(row, COLUMN_MAP, 'official_email'),
                    'department': department
                }
                conflicts.append(conflict_data)
                continue

            raw_password = generate_password()
            official_email = get_column_value(row, COLUMN_MAP, 'official_email')
            login_email = official_email if official_email else f"{employee_id}@university.edu"

            # Hash the password before saving
            hashed_password = generate_password_hash(raw_password)
            
            teacher = Employee(
                employee_id=employee_id,
                name=get_column_value(row, COLUMN_MAP, 'name'),
                department=department,
                post=get_column_value(row, COLUMN_MAP, 'post'),
                mobile=get_column_value(row, COLUMN_MAP, 'mobile'),
                official_email=official_email,
                email=login_email.lower(),
                password=hashed_password,  # Save hashed password
                raw_password=raw_password,  # Store raw password for reference only
                role='faculty'
            )
            teachers_to_create.append(teacher)

        if teachers_to_create:
            Employee.objects.insert(teachers_to_create)
            # Emit socket event for real-time updates using safe function
            safe_socket_emit('teachers_uploaded', {
                'count': len(teachers_to_create),
                'uploader': current_user.name,
                'department': department
            })

        message = f"Process complete. Successfully created {len(teachers_to_create)} new teachers."
        return jsonify({"message": message, "conflicts": conflicts, "errors": errors}), 201

    except Exception as e:
        current_app.logger.error(f"Error in upload_teacher_details: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@data_upload_bp.route("/teachers/add-manual", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def add_teacher_manual(current_user):
    try:
        data = request.json
        employee_id = data.get('employee_id')
        
        if Employee.objects(employee_id=employee_id).first():
            existing_teacher = Employee.objects.get(employee_id=employee_id)
            return jsonify({
                "error": f"Teacher with Employee ID '{employee_id}' already exists.",
                "existing_data": existing_teacher.to_mongo().to_dict()
            }), 409

        raw_password = generate_password()
        # Hash the password before saving
        hashed_password = generate_password_hash(raw_password)
        
        teacher = Employee(
            department=data.get('department'),
            employee_id=employee_id,
            name=data.get('name'),
            post=data.get('post'),
            mobile=data.get('mobile'),
            official_email=data.get('official_email', '').lower(),
            email=data.get('official_email', '').lower(),
            password=hashed_password,  # Save hashed password
            raw_password=raw_password,  # Store raw password for reference only
            role=data.get('role', 'faculty')
        )
        teacher.save()
        
        # Emit socket event for real-time updates using safe function
        safe_socket_emit('teacher_added', {
            'id': str(teacher.id),
            'name': teacher.name,
            'employee_id': teacher.employee_id,
            'uploader': current_user.name
        })
        
        return jsonify({"message": f"Successfully created teacher '{data.get('name')}'."}), 201
    except Exception as e:
        current_app.logger.error(f"Error in add_teacher_manual: {str(e)}")
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/teachers/update-manual/<employee_id>", methods=["PUT"])
@token_required
@role_required(['admin', 'academic'])
def update_teacher_manual(current_user, employee_id):
    try:
        data = request.json
        teacher = Employee.objects(employee_id=employee_id).first()
        if not teacher:
            return jsonify({"error": "Teacher not found."}), 404
            
        teacher.department = data.get('department', teacher.department)
        teacher.name = data.get('name', teacher.name)
        teacher.post = data.get('post', teacher.post)
        teacher.mobile = data.get('mobile', teacher.mobile)
        teacher.official_email = data.get('official_email', teacher.official_email).lower()
        teacher.email = data.get('official_email', teacher.email).lower()
        teacher.role = data.get('role', teacher.role)

        teacher.save()
        
        # Emit socket event for real-time updates using safe function
        safe_socket_emit('teacher_updated', {
            'id': str(teacher.id),
            'name': teacher.name,
            'employee_id': teacher.employee_id,
            'updater': current_user.name
        })
        
        return jsonify({"message": f"Successfully updated teacher '{teacher.name}'."}), 200
    except Exception as e:
        current_app.logger.error(f"Error in update_teacher_manual: {str(e)}")
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/teachers/batch-update", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def batch_update_teachers(current_user):
    try:
        teachers_to_update = request.json
        updated_count = 0
        failed_ids = []

        for teacher_data in teachers_to_update:
            employee_id = teacher_data.get('employee_id')
            if not employee_id: continue

            teacher = Employee.objects(employee_id=employee_id).first()
            if teacher:
                teacher.name = teacher_data.get('name', teacher.name)
                teacher.department = teacher_data.get('department', teacher.department)
                teacher.post = teacher_data.get('post', teacher.post)
                teacher.mobile = teacher_data.get('mobile', teacher.mobile)
                official_email = teacher_data.get('official_email', teacher.official_email).lower()
                if official_email:
                    teacher.official_email = official_email
                    teacher.email = official_email
                teacher.role = teacher_data.get('role', teacher.role)
                
                teacher.save()
                updated_count += 1
            else:
                failed_ids.append(employee_id)
        
        message = f"Successfully updated {updated_count} teacher(s)."
        if failed_ids:
            message += f" Failed to find teachers with IDs: {', '.join(failed_ids)}."
            
        # Emit socket event for real-time updates using safe function
        safe_socket_emit('teachers_batch_updated', {
            'count': updated_count,
            'updater': current_user.name
        })
            
        return jsonify({"message": message}), 200

    except Exception as e:
        current_app.logger.error(f"Error in batch_update_teachers: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500