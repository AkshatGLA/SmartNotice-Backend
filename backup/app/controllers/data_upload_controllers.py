# ===============================================================
# Controller for Data Upload Functionality (Improved Debugging)
# File: app/controllers/data_upload_controller.py
# ===============================================================

from flask import Blueprint, request, jsonify, current_app
from mongoengine import Document, EmbeddedDocument, EmbeddedDocumentField, StringField, ListField, DateTimeField, EmailField
from werkzeug.security import generate_password_hash
import pandas as pd
import random
import string
import traceback
import datetime
from functools import wraps
import jwt
from bson import ObjectId
from ..models.user_model import User
from ..models.department_model import Department
from ..models.course_model import Course
from ..models.student_model import Student
from ..models.employee_model import Employee

# --- Authentication & Helper Functions ---

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
            
        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.objects(id=ObjectId(data['user_id'])).first()
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
        except Exception as e:
            return jsonify({'message': f'Token is invalid! {str(e)}'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(current_user, *args, **kwargs):
            if current_user.role not in roles:
                return jsonify({'message': 'Unauthorized access!'}), 403
            return f(current_user, *args, **kwargs)
        return decorated_function
    return decorator

def generate_password(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def get_column_value(row, column_map, field_name):
    for column_name in column_map.get(field_name, []):
        if column_name in row:
            return str(row[column_name]).strip()
    return ""

# --- Blueprint Definition ---
data_upload_bp = Blueprint('data_upload_api', __name__)

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
        'father_mobile': ['father mob.', 'father_mobile', "father's mobile"],
        'mother_name': ['mothers name', 'mother_name', "mother's name"],
        'mother_contact': ['mother contact', 'mother_contact'],
        'dob': ['dob', 'date of birth', 'birth date'],
        'gender': ['gender', 'sex'],
        'address': ['address', 'residential address']
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

        print(f"DEBUG: Detected column headers in file: {list(df.columns)}")

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
                conflict_data = {
                    'branch': department, 'course': course, 'year': year, 'section': section,
                    'univ_roll_no': univ_roll_no,
                    'name': get_column_value(row, COLUMN_MAP, 'name'),
                    'father_name': get_column_value(row, COLUMN_MAP, 'father_name'),
                    'mother_name': get_column_value(row, COLUMN_MAP, 'mother_name'),
                    'student_mobile': get_column_value(row, COLUMN_MAP, 'student_mobile'),
                    'father_mobile': get_column_value(row, COLUMN_MAP, 'father_mobile'),
                    'mother_contact': get_column_value(row, COLUMN_MAP, 'mother_contact'),
                    'official_email': get_column_value(row, COLUMN_MAP, 'email'),
                    'dob': get_column_value(row, COLUMN_MAP, 'dob'),
                    'gender': get_column_value(row, COLUMN_MAP, 'gender'),
                    'address': get_column_value(row, COLUMN_MAP, 'address')
                }
                conflicts.append(conflict_data)
                continue

            raw_password = generate_password()
            official_email = get_column_value(row, COLUMN_MAP, 'email')
            login_email = official_email if official_email else f"{univ_roll_no}@university.edu"
            
            student = Student(
                branch=department,
                course=course,
                year=year,
                section=section,
                univ_roll_no=univ_roll_no,
                name=get_column_value(row, COLUMN_MAP, 'name'),
                father_name=get_column_value(row, COLUMN_MAP, 'father_name'),
                mother_name=get_column_value(row, COLUMN_MAP, 'mother_name'),
                student_mobile=get_column_value(row, COLUMN_MAP, 'student_mobile'),
                father_mobile=get_column_value(row, COLUMN_MAP, 'father_mobile'),
                mother_contact=get_column_value(row, COLUMN_MAP, 'mother_contact'),
                official_email=official_email,
                email=login_email.lower(),
                password=generate_password_hash(raw_password),
                raw_password=raw_password,
                dob=datetime.datetime.strptime(get_column_value(row, COLUMN_MAP, 'dob'), '%Y-%m-%d') if get_column_value(row, COLUMN_MAP, 'dob') else None,
                gender=get_column_value(row, COLUMN_MAP, 'gender'),
                address=get_column_value(row, COLUMN_MAP, 'address')
            )
            students_to_create.append(student)

        if students_to_create:
            Student.objects.insert(students_to_create)

        message = f"Process complete. Successfully created {len(students_to_create)} new students."
        if errors:
            message += f" Encountered {len(errors)} errors."
        if not students_to_create and not conflicts and errors:
             message = f"No new students were added. The file may have been empty or contained only existing records. Encountered {len(errors)} errors."

        return jsonify({"message": message, "conflicts": conflicts, "errors": errors}), 201

    except Exception as e:
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
                "existing_data": existing_student.to_mongo().to_dict()
            }), 409

        raw_password = generate_password()
        student = Student(
            branch=data.get('department'),
            course=data.get('course'),
            year=data.get('year'),
            section=data.get('section'),
            name=data.get('name'),
            univ_roll_no=univ_roll_no,
            student_mobile=data.get('student_mobile'),
            father_name=data.get('father_name'),
            mother_name=data.get('mother_name'),
            father_mobile=data.get('father_mobile'),
            mother_contact=data.get('mother_contact'),
            official_email=data.get('official_email', '').lower(),
            email=data.get('official_email', '').lower(),
            password=generate_password_hash(raw_password),
            raw_password=raw_password,
            dob=datetime.datetime.strptime(data.get('dob'), '%Y-%m-%d') if data.get('dob') else None,
            gender=data.get('gender'),
            address=data.get('address')
        )
        student.save()
        return jsonify({"message": f"Successfully created student '{data.get('name')}'."}), 201
    except Exception as e:
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
        student.mother_name = data.get('mother_name', student.mother_name)
        student.father_mobile = data.get('father_mobile', student.father_mobile)
        student.mother_contact = data.get('mother_contact', student.mother_contact)
        official_email = data.get('official_email', student.official_email).lower()
        if official_email:
            student.official_email = official_email
            student.email = official_email
        student.dob = datetime.datetime.strptime(data.get('dob'), '%Y-%m-%d') if data.get('dob') else student.dob
        student.gender = data.get('gender', student.gender)
        student.address = data.get('address', student.address)
        
        student.save()
        return jsonify({"message": f"Successfully updated student '{student.name}'."}), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/employees/upload-details", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def upload_employee_details(current_user):
    COLUMN_MAP = {
        'employee_id': ['employee id', 'employee_id', 'emp_id', 'employee number'],
        'name': ['name', 'teacher name', 'teacher_name', 'full name'],
        'post': ['post', 'designation'],
        'mobile': ['mobile', 'contact no', 'phone', 'mobile number'],
        'official_email': ['email', 'official email', 'official_email', 'email id'],
        'specialization': ['specialization', 'subject', 'expertise']
    }
    try:
        department = request.form.get('department')
        file = request.files.get('file')

        if not all([department, file]):
            return jsonify({"error": "Department and file are required."}), 400

        df = pd.read_excel(file) if file.filename.lower().endswith(('.xlsx', '.xls')) else pd.read_csv(file)
        df.columns = [str(col).strip().lower() for col in df.columns]
        df = df.fillna('')

        employees_to_create = []
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
                    'specialization': get_column_value(row, COLUMN_MAP, 'specialization'),
                    'department': department
                }
                conflicts.append(conflict_data)
                continue

            raw_password = generate_password()
            official_email = get_column_value(row, COLUMN_MAP, 'official_email')
            login_email = official_email if official_email else f"{employee_id}@university.edu"

            employee = Employee(
                employee_id=employee_id,
                name=get_column_value(row, COLUMN_MAP, 'name'),
                department=department,
                post=get_column_value(row, COLUMN_MAP, 'post'),
                specialization=get_column_value(row, COLUMN_MAP, 'specialization'),
                mobile=get_column_value(row, COLUMN_MAP, 'mobile'),
                official_email=official_email,
                email=login_email.lower(),
                password=generate_password_hash(raw_password),
                raw_password=raw_password,
                role='faculty'  # Default role for uploaded employees
            )
            employees_to_create.append(employee)

        if employees_to_create:
            Employee.objects.insert(employees_to_create)

        message = f"Process complete. Successfully created {len(employees_to_create)} new employees."
        return jsonify({"message": message, "conflicts": conflicts, "errors": errors}), 201

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500

@data_upload_bp.route("/employees/add-manual", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def add_employee_manual(current_user):
    try:
        data = request.json
        employee_id = data.get('employee_id')
        
        if Employee.objects(employee_id=employee_id).first():
            existing_employee = Employee.objects.get(employee_id=employee_id)
            return jsonify({
                "error": f"Employee with ID '{employee_id}' already exists.",
                "existing_data": existing_employee.to_mongo().to_dict()
            }), 409

        raw_password = generate_password()
        employee = Employee(
            department=data.get('department'),
            employee_id=employee_id,
            name=data.get('name'),
            post=data.get('post'),
            specialization=data.get('specialization'),
            mobile=data.get('mobile'),
            official_email=data.get('official_email', '').lower(),
            email=data.get('official_email', '').lower(),
            password=generate_password_hash(raw_password),
            raw_password=raw_password,
            role=data.get('role', 'faculty')
        )
        employee.save()
        return jsonify({"message": f"Successfully created employee '{data.get('name')}'."}), 201
    except Exception as e:
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/employees/update-manual/<employee_id>", methods=["PUT"])
@token_required
@role_required(['admin', 'academic'])
def update_employee_manual(current_user, employee_id):
    try:
        data = request.json
        employee = Employee.objects(employee_id=employee_id).first()
        if not employee:
            return jsonify({"error": "Employee not found."}), 404
            
        employee.department = data.get('department', employee.department)
        employee.name = data.get('name', employee.name)
        employee.post = data.get('post', employee.post)
        employee.specialization = data.get('specialization', employee.specialization)
        employee.mobile = data.get('mobile', employee.mobile)
        official_email = data.get('official_email', employee.official_email).lower()
        if official_email:
            employee.official_email = official_email
            employee.email = official_email
        employee.role = data.get('role', employee.role)

        employee.save()
        return jsonify({"message": f"Successfully updated employee '{employee.name}'."}), 200
    except Exception as e:
        return jsonify({"error": f"An unexpected server error: {str(e)}"}), 500

@data_upload_bp.route("/employees/batch-update", methods=["POST"])
@token_required
@role_required(['admin', 'academic'])
def batch_update_employees(current_user):
    try:
        employees_to_update = request.json
        updated_count = 0
        failed_ids = []

        for employee_data in employees_to_update:
            employee_id = employee_data.get('employee_id')
            if not employee_id: continue

            employee = Employee.objects(employee_id=employee_id).first()
            if employee:
                employee.name = employee_data.get('name', employee.name)
                employee.department = employee_data.get('department', employee.department)
                employee.post = employee_data.get('post', employee.post)
                employee.specialization = employee_data.get('specialization', employee.specialization)
                employee.mobile = employee_data.get('mobile', employee.mobile)
                official_email = employee_data.get('official_email', employee.official_email).lower()
                if official_email:
                    employee.official_email = official_email
                    employee.email = official_email
                employee.role = employee_data.get('role', employee.role)
                
                employee.save()
                updated_count += 1
            else:
                failed_ids.append(employee_id)
        
        message = f"Successfully updated {updated_count} employee(s)."
        if failed_ids:
            message += f" Failed to find employees with IDs: {', '.join(failed_ids)}."
            
        return jsonify({"message": message}), 200

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"An unexpected server error occurred: {str(e)}"}), 500