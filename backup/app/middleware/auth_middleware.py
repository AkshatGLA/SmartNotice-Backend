from functools import wraps
from flask import jsonify, request
import jwt
from bson import ObjectId
from ..models.user_model import User
from ..models.student_model import Student
from ..models.employee_model import Employee
from config import Config
from datetime import datetime

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization', '')
        
        # Extract token from header
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Token is missing or malformed!',
                'code': 'AUTH_HEADER_MISSING'
            }), 401
            
        try:
            # Decode token and verify
            data = jwt.decode(token, Config.SECRET_KEY, algorithms=["HS256"])
            
            # Check token expiration
            if 'exp' not in data or datetime.utcnow() > datetime.utcfromtimestamp(data['exp']):
                return jsonify({
                    'status': 'error',
                    'message': 'Token has expired!',
                    'code': 'TOKEN_EXPIRED'
                }), 401
                
            # Find user based on role in token
            user = None
            if data.get('role') == 'student':
                user = Student.objects(id=ObjectId(data['user_id'])).first()
            elif data.get('role') == 'employee':
                user = Employee.objects(id=ObjectId(data['user_id'])).first()
            else:
                # Fallback to User model for backward compatibility
                user = User.objects(id=ObjectId(data['user_id'])).first()
            
            if not user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not found!',
                    'code': 'USER_NOT_FOUND'
                }), 404
                
            # Add additional security checks
            if 'ip' in data and request.remote_addr != data['ip']:
                return jsonify({
                    'status': 'error',
                    'message': 'Suspicious activity detected!',
                    'code': 'IP_MISMATCH'
                }), 401
                
            # Add user object to kwargs for route access
            kwargs['current_user'] = user
            
        except jwt.ExpiredSignatureError:
            return jsonify({
                'status': 'error',
                'message': 'Token has expired!',
                'code': 'TOKEN_EXPIRED'
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid token!',
                'code': 'INVALID_TOKEN'
            }), 401
        except Exception as e:
            print(f"Token validation error: {str(e)}")
            return jsonify({
                'status': 'error',
                'message': 'Token validation failed!',
                'code': 'TOKEN_VALIDATION_FAILED'
            }), 401
            
        return f(*args, **kwargs)
    return decorated

def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not authenticated!',
                    'code': 'UNAUTHENTICATED'
                }), 401
                
            # Handle both User model and Student/Employee models
            user_role = getattr(current_user, 'role', None)
            if not user_role or user_role.lower() not in [r.lower() for r in roles]:
                return jsonify({
                    'status': 'error',
                    'message': 'Unauthorized access!',
                    'code': 'UNAUTHORIZED'
                }), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator

def department_required(departments):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            current_user = kwargs.get('current_user')
            if not current_user:
                return jsonify({
                    'status': 'error',
                    'message': 'User not authenticated!',
                    'code': 'UNAUTHENTICATED'
                }), 401
                
            # Check department for employees
            user_dept = getattr(current_user, 'department', None)
            if not user_dept or user_dept.lower() not in [d.lower() for d in departments]:
                return jsonify({
                    'status': 'error',
                    'message': 'Department access restricted!',
                    'code': 'DEPARTMENT_RESTRICTED'
                }), 403
                
            return f(*args, **kwargs)
        return decorated
    return decorator

def student_only(f):
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not isinstance(current_user, Student):
            return jsonify({
                'status': 'error',
                'message': 'This route is for students only!',
                'code': 'STUDENT_ONLY'
            }), 403
        return f(*args, **kwargs)
    return decorated

def employee_only(f):
    @wraps(f)
    @token_required
    def decorated(*args, **kwargs):
        current_user = kwargs.get('current_user')
        if not isinstance(current_user, Employee):
            return jsonify({
                'status': 'error',
                'message': 'This route is for employees only!',
                'code': 'EMPLOYEE_ONLY'
            }), 403
        return f(*args, **kwargs)
    return decorated