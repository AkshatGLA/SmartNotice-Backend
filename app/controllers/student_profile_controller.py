from flask import Blueprint, request, jsonify
import logging
from ..models.student_model import Student
from ..middleware.auth_middleware import token_required

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

profile_bp = Blueprint('student_profile', __name__, url_prefix='/api/student-profile')

@profile_bp.route("", methods=["GET"])
@token_required
def get_profile(current_user):
    try:
        logger.info(f"Fetching profile for student ID: {current_user.id}")
        student = Student.objects(id=current_user.id).exclude('password', 'raw_password').first()
        
        if not student:
            logger.warning(f"Student not found for ID: {current_user.id}")
            return jsonify({"error": "Student not found"}), 404
        
        # Convert notices to just IDs to avoid circular references
        profile_data = {
            "id": str(student.id),
            "univ_roll_no": student.univ_roll_no,
            "class_roll_no": student.class_roll_no,
            "name": student.name,
            "name_hindi": student.name_hindi,
            "email": student.email,
            "official_email": student.official_email,
            "course": student.course,
            "branch": student.branch,
            "year": student.year,
            "section": student.section,
            "dob": student.dob.isoformat() if student.dob else None,
            "gender": student.gender,
            "address": student.address,
            "student_mobile": student.student_mobile,
            "student_alt_contact": student.student_alt_contact,
            "father_name": student.father_name,
            "father_mobile": student.father_mobile,
            "father_alt_contact": student.father_alt_contact,
            "mother_name": student.mother_name,
            "mother_contact": student.mother_contact,
            "high_school": student.high_school or {},
            "intermediate": student.intermediate or {},
            "graduation": student.graduation or {},
            "lib_code": student.lib_code,
            "last_medium": student.last_medium,
            "admission_office": student.admission_office,
            "target_company": student.target_company,
            "hobbies": student.hobbies,
            "ratings": student.ratings or {},
            "created_at": student.created_at.isoformat(),
            "notices": [str(notice.id) for notice in student.notices] if student.notices else []
        }
        
        logger.info(f"Successfully fetched profile for student: {student.univ_roll_no}")
        return jsonify(profile_data), 200
        
    except Exception as e:
        logger.error(f"Error fetching profile: {str(e)}", exc_info=True)
        return jsonify({
            "error": "Failed to fetch profile",
            "details": str(e)
        }), 500

@profile_bp.route("", methods=["PUT"])
@token_required
def update_profile(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        allowed_fields = {
            'name', 'name_hindi', 'official_email', 'student_mobile', 
            'student_alt_contact', 'father_name', 'father_mobile', 
            'father_alt_contact', 'mother_name', 'mother_contact',
            'address', 'hobbies', 'target_company', 'dob', 'gender'
        }
        
        update_data = {k: v for k, v in data.items() if k in allowed_fields}
        
        student = Student.objects(id=current_user.id).first()
        if not student:
            return jsonify({"error": "Student not found"}), 404
            
        for field, value in update_data.items():
            setattr(student, field, value)
        
        student.save()
        
        return jsonify({
            "message": "Profile updated successfully",
            "student": {
                "id": str(student.id),
                "name": student.name,
                "email": student.email,
                "official_email": student.official_email
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating profile: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@profile_bp.route("/academic-history", methods=["PUT"])
@token_required
def update_academic_history(current_user):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        student = Student.objects(id=current_user.id).first()
        if not student:
            return jsonify({"error": "Student not found"}), 404
            
        if 'high_school' in data:
            student.high_school = data['high_school']
        if 'intermediate' in data:
            student.intermediate = data['intermediate']
        if 'graduation' in data:
            student.graduation = data['graduation']
            
        student.save()
        
        return jsonify({
            "message": "Academic history updated successfully",
            "high_school": student.high_school,
            "intermediate": student.intermediate,
            "graduation": student.graduation
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating academic history: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500