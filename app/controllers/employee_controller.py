from flask import Blueprint, jsonify
from ..models.employee_model import Employee
from ..middleware.auth_middleware import token_required

employee_bp = Blueprint('employees', __name__, url_prefix='/api/employees')

@employee_bp.route('', methods=['GET'])
@token_required
def get_employees(current_user):
    """
    Get all employees (for approver selection)
    """
    employees = Employee.objects().only(
        '_id', 'name', 'department', 'post', 'official_email', 'role'
    ).exclude('password', 'raw_password')
    
    # Filter out non-approvers if needed
    # approvers = [emp for emp in employees if emp.role in ['admin', 'academic']]
    
    # return jsonify([emp.to_dict() for emp in approvers]), 200


    return jsonify([emp.to_mongo().to_dict() for emp in employees]), 200


@employee_bp.route('/me', methods=['GET'])
@token_required
def get_current_employee(current_user):
    """
    Get current logged-in employee details
    """
    if not isinstance(current_user, Employee):
        return jsonify({"error": "Employee access only"}), 403
    
    # Return minimal required fields for the dashboard
    return jsonify({
        "id": str(current_user.id),
        "employee_id": current_user.employee_id,
        "name": current_user.name,
        "department": current_user.department,
        "post": current_user.post,
        "email": current_user.email,
        "official_email": current_user.official_email,
        "role": current_user.role,
        "pending_approvals": get_pending_approvals_count(current_user.id)
    }), 200
        

def get_pending_approvals_count(employee_id):
    # Implement logic to count pending approvals for this employee
    return 3
    # except Exception as e:
    #     return jsonify({"error": str(e)}), 500

@employee_bp.route('/<employee_id>', methods=['GET'])
@token_required
def get_employee(current_user, employee_id):
    """
    Get single employee details
    """
    employee = Employee.objects(id=employee_id).exclude('password', 'raw_password').first()
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
    
    return jsonify(employee.to_mongo().to_dict()), 200
