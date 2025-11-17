from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from bson import ObjectId
from ..models.user_model import User
from config import Config
from ..models.student_model import Student
from ..middleware.auth_middleware import token_required
from ..models.employee_model import Employee
from app import app

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route("/signup", methods=["POST"])
def signup():
    try:
        data = request.json

        # Validate required fields
        required_fields = ['name', 'email', 'password', 'role']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Missing required fields"}), 400

        # Validate role
        valid_roles = ['academic', 'fees', 'exam', 'placement']
        if data['role'] not in valid_roles:
            return jsonify({"error": "Invalid role specified"}), 400

        # Check if email exists
        if User.objects(email=data['email']).first():
            return jsonify({"error": "Email already exists"}), 400

        # Create new user
        hashed_password = generate_password_hash(data['password'])
        user = User(
            name=data['name'],
            email=data['email'],
            password=hashed_password,
            role=data['role']
        )
        user.save()

        return jsonify({
            "message": "User created successfully",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.json

        # Validate required fields
        if not all(field in data for field in ['email', 'password', 'role']):
            return jsonify({"error": "Email, password and role are required"}), 400

        user = User.objects(email=data['email']).first()

        if not user or not check_password_hash(user.password, data['password']):
            return jsonify({"error": "Invalid credentials"}), 401

        # Verify that the provided role matches the user's actual role
        if user.role != data['role']:
            return jsonify({
                "error": f"Invalid role for this user. Your account is for {user.role} department"
            }), 403

        # Generate tokens
        access_token = jwt.encode({
            'user_id': str(user.id),
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }, Config.SECRET_KEY)

        refresh_token = jwt.encode({
            'user_id': str(user.id),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, Config.SECRET_KEY)

        return jsonify({
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login/student", methods=["POST"])
def login_student():
    try:
        data = request.json

        if not all(field in data for field in ['univ_roll_no', 'password']):
            return jsonify({"error": "University roll number and password are required"}), 400

        student = Student.objects(univ_roll_no=data['univ_roll_no']).first()

        if not student or not check_password_hash(student.password, data['password']):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate tokens
        access_token = jwt.encode({
            'user_id': str(student.id),
            'role': 'student',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }, Config.SECRET_KEY)

        refresh_token = jwt.encode({
            'user_id': str(student.id),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, Config.SECRET_KEY)

        return jsonify({
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "user": {
                "id": str(student.id),
                "name": student.name,
                "email": student.email,
                "official_email": student.official_email,
                "role": 'student',
                "univ_roll_no": student.univ_roll_no,
                "course": student.course,
                "branch": student.branch,
                "year": student.year,
                "section": student.section
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/login/employee", methods=["POST"])
def login_employee():
    try:
        data = request.json

        # Validate required fields
        if not all(field in data for field in ['employee_id', 'password']):
            return jsonify({"error": "Employee ID and password are required"}), 400

        employee = Employee.objects(employee_id=data['employee_id']).first()

        if not employee:
            return jsonify({"error": "Invalid credentials"}), 401

        # Verify password - this will handle the scrypt hash from your example
    # Only checks hashed password
        if not employee.check_password(data['password']):
            return jsonify({"error": "Invalid credentials"}), 401

        # Generate tokens
        access_token = jwt.encode({
            'user_id': str(employee.id),
            'role': employee.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }, Config.SECRET_KEY)

        refresh_token = jwt.encode({
            'user_id': str(employee.id),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
        }, Config.SECRET_KEY)

        return jsonify({
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "user": {
                "id": str(employee.id),
                "employee_id": employee.employee_id,
                "name": employee.name,
                "email": employee.email,
                "official_email": employee.official_email,
                "role": employee.role,
                "department": employee.department,
                "post": employee.post,
                "specialization": employee.specialization,
                "mobile": employee.mobile
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    try:
        refresh_token = request.json.get('refreshToken')
        if not refresh_token:
            return jsonify({"error": "Refresh token required"}), 400

        data = jwt.decode(
            refresh_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = User.objects(id=ObjectId(data['user_id'])).first()

        if not user:
            return jsonify({"error": "Invalid user"}), 401

        new_access_token = jwt.encode({
            'user_id': str(user.id),
            'role': user.role,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }, app.config['SECRET_KEY'])

        return jsonify({
            "accessToken": new_access_token,
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Refresh token expired"}), 401
    except Exception as e:
        return jsonify({"error": "Token refresh failed"}), 400


@auth_bp.route("/current-user", methods=["GET"])
@token_required
def get_current_user(current_user):
    try:
        return jsonify({
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@auth_bp.route("/logout", methods=["POST"])
def logout():
    return jsonify({"message": "Logged out successfully"}), 200
