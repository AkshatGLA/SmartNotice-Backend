from flask import Blueprint, jsonify
from ..models.student_model import Student
from ..middleware.auth_middleware import token_required

university_bp = Blueprint('university', __name__, url_prefix='/api')

@university_bp.route('/years', methods=['GET'])
@token_required
def get_years(current_user):
    try:
        years = Student.objects.distinct('year')
        sorted_years = sorted([y for y in years if y])
        return jsonify(sorted_years), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@university_bp.route('/sections', methods=['GET'])
@token_required
def get_sections(current_user):
    try:
        sections = Student.objects.distinct('section')
        sorted_sections = sorted([s for s in sections if s])
        return jsonify(sorted_sections), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500