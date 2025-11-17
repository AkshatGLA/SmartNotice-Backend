# from flask import Blueprint, request, jsonify, send_file
# import os
# import pandas as pd
# import random
# import string
# from werkzeug.security import generate_password_hash
# from ..models.student_model import Student
# from ..middleware.auth_middleware import token_required, role_required
# from datetime import datetime, timedelta

# student_bp = Blueprint('students', __name__, url_prefix='/api/students')

# COLUMN_MAP = {
#     'name': ['name', 'student name', 'student_name'],
#     'univ_roll_no': ['univ_roll_no', 'univ rollno', 'univ. rollno.', 'roll no', 'roll_no'],
#     'class_roll_no': ['class_roll_no', 'class roll no'],
#     'email': ['email', 'email id', 'official_email', 'official email-id'],
#     'father_name': ['fathers name', 'father_name', 'father name'],
#     'student_mobile': ['stu. mob.', 'student_mobile', 'mobile no', 'student contact'],
#     'father_mobile': ['father mob.', 'father_mobile', 'father contact']
# }

# def generate_password(length=6):
#     chars = string.ascii_letters + string.digits
#     return ''.join(random.choice(chars) for _ in range(length))

# @student_bp.route("/upload-details", methods=["POST"])
# @token_required
# @role_required(['admin'])
# def upload_student_details(current_user):
#     try:
#         department = request.form.get('department')
#         course = request.form.get('course')
#         year = request.form.get('year')
#         section = request.form.get('section')
#         file = request.files.get('file')

#         if not all([department, course, year, section, file]):
#             return jsonify({"error": "Missing required form data or file."}), 400

#         try:
#             if file.filename.lower().endswith('.csv'):
#                 df = pd.read_csv(file, encoding='utf-8', skipinitialspace=True)
#             else:
#                 df = pd.read_excel(file)
#         except Exception as e:
#             return jsonify({"error": f"Could not read the file: {str(e)}"}), 400

#         df.columns = [col.strip().lower() for col in df.columns]
#         df = df.fillna('')

#         students_to_create = []
#         errors = []

#         for index, row in df.iterrows():
#             univ_roll_no = get_column_value(row, COLUMN_MAP, 'univ_roll_no')
#             if not univ_roll_no:
#                 errors.append(f"Row {index + 2}: Missing University Roll Number")
#                 continue

#             if Student.objects(univ_roll_no=univ_roll_no).first():
#                 errors.append(f"Row {index + 2}: Student {univ_roll_no} already exists")
#                 continue

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

#         if students_to_create:
#             Student.objects.insert(students_to_create)

#         message = f"Created {len(students_to_create)} new students." if students_to_create else "No new students added."
#         if errors:
#             message += f" {len(errors)} rows had issues."

#         return jsonify({
#             "message": message,
#             "created": len(students_to_create),
#             "errors": errors
#         }), 201

#     except Exception as e:
#         return jsonify({"error": f"Server error: {str(e)}"}), 500

# @student_bp.route("/template", methods=["GET"])
# @token_required
# def download_student_template(current_user):
#     try:
#         template_path = os.path.join(os.path.dirname(__file__), '../../static/templates/student_template.xlsx')
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
    
# @student_bp.route("/me", methods=["GET"])
# @token_required
# def get_current_student(current_user):
#     try:
#         # Find the student by their ID (stored in current_user from token)
#         student = Student.objects(id=current_user.id).exclude('password', 'raw_password').first()
        
#         if not student:
#             return jsonify({"error": "Student not found"}), 404
            
#         return jsonify({
#             "id": str(student.id),
#             "univ_roll_no": student.univ_roll_no,
#             "name": student.name,
#             "email": student.email,
#             "official_email": student.official_email,
#             "course": student.course,
#             "branch": student.branch,
#             "year": student.year,
#             "section": student.section,
#             "gender": student.gender,
#             "dob": student.dob.isoformat() if student.dob else None,
#             "address": student.address,
#             "student_mobile": student.student_mobile,
#             "father_mobile": student.father_mobile
#         }), 200
        
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    


# def get_column_value(row, column_map, field_name):
#     for column_name in column_map[field_name]:
#         if column_name in row:
#             return str(row[column_name]).strip()
#     return ""