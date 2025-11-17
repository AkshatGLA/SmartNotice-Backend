from flask import Blueprint, jsonify
from ..models.department_model import Department, Course
from ..middleware.auth_middleware import token_required

department_bp = Blueprint('departments', __name__, url_prefix='/api/departments')

@department_bp.route("", methods=["GET"])
@token_required
def get_departments(current_user):
    try:
        departments = Department.objects.only('name', 'code').order_by('name')
        return jsonify([{"name": d.name, "code": d.code} for d in departments]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@department_bp.route("/<code>/courses", methods=["GET"])
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

@department_bp.route("/setup/seed-departments", methods=["GET"])
def seed_departments():
    if Department.objects.count() > 0:
        return jsonify({"message": "Departments already exist"}), 400

    department_data = [
        {"name": "Computer Engineering & Applications", "code": "CEA", "courses": [
            {"name": "B.Tech in CSE", "code": "BTECH_CSE"},
            {"name": "B.Tech (Hons.) CSE (Specialization in AI & Analytics)", "code": "BTECH_HONS_AI"},
            {"name": "B.Tech CSE (Specialization in AIML)", "code": "BTECH_AIML"},
            {"name": "B.Tech Lateral Entry – CSE", "code": "BTECH_LAT_CSE"},
            {"name": "BCA / BCA (Hons./By Research)", "code": "BCA"},
            {"name": "BCA Data Science", "code": "BCA_DS"},
            {"name": "BCA in Digital Marketing", "code": "BCA_DM"}
        ]},
        {"name": "Electronics & Communication Engineering (ECE)", "code": "ECE", "courses": [
            {"name": "B.Tech in Electronics and Computer Engineering", "code": "BTECH_ECS"},
            {"name": "B.Tech EC (Minor in CS)", "code": "BTECH_EC_CS"},
            {"name": "B.Tech EC (Specialization in VLSI)", "code": "BTECH_EC_VLSI"},
            {"name": "B.Tech in ECE", "code": "BTECH_ECE"},
            {"name": "B.Tech Lateral Entry – EC, ECE", "code": "BTECH_LAT_ECE"}
        ]},
        {"name": "Electrical Engineering", "code": "EE", "courses": [
            {"name": "B.Tech in EE", "code": "BTECH_EE"},
            {"name": "B.Tech in EEE", "code": "BTECH_EEE"},
            {"name": "B.Tech EE (EV Technology)", "code": "BTECH_EE_EV"},
            {"name": "B.Tech EE (Minor in CS)", "code": "BTECH_EE_CS"},
            {"name": "B.Tech Lateral Entry – EE, EEE, EE (EV Technology)", "code": "BTECH_LAT_EE"}
        ]},
        {"name": "Mechanical Engineering", "code": "ME", "courses": [
            {"name": "B.Tech in ME", "code": "BTECH_ME"},
            {"name": "B.Tech ME (Minor in CS)", "code": "BTECH_ME_CS"},
            {"name": "B.Tech ME (Automobile)", "code": "BTECH_ME_AUTO"},
            {"name": "B.Tech ME (Mechatronics)", "code": "BTECH_ME_MECHA"},
            {"name": "B.Tech Lateral Entry – ME", "code": "BTECH_LAT_ME"},
            {"name": "ME in Smart Manufacturing", "code": "MTECH_SM"}
        ]},
        {"name": "Civil Engineering", "code": "CE", "courses": [
            {"name": "B.Tech in CE", "code": "BTECH_CE"},
            {"name": "B.Tech Lateral Entry – CE", "code": "BTECH_LAT_CE"}
        ]},
        {"name": "Biotechnology", "code": "BT", "courses": [
            {"name": "B.Tech in Biotech", "code": "BTECH_BT"},
            {"name": "B.Tech Lateral Entry – Biotech", "code": "BTECH_LAT_BT"},
            {"name": "B.Sc. Biotech / B.Sc. Biotech (Hons./By Research)", "code": "BSC_BT"}
        ]},
        {"name": "Pharmaceutical Sciences", "code": "PHARM", "courses": [
            {"name": "B.Pharm", "code": "BPHARM"},
            {"name": "B.Pharm (Lateral Entry)", "code": "BPHARM_LAT"},
            {"name": "Pharm.D", "code": "PHARMD"}
        ]},
        {"name": "Faculty of Agricultural Sciences", "code": "AGRI", "courses": [
            {"name": "B.Sc. (Hons.) Agriculture", "code": "BSC_AGRI"}
        ]},
        {"name": "Physics / Chemistry / Mathematics", "code": "SCI", "courses": [
            {"name": "B.Sc. Physics / B.Sc. Physics (Hons./By Research)", "code": "BSC_PHY"},
            {"name": "B.Sc. Chemistry / B.Sc. Chemistry (Hons./By Research)", "code": "BSC_CHEM"},
            {"name": "B.Sc. Maths / B.Sc. Maths (Hons./By Research in DS)", "code": "BSC_MATH"}
        ]},
        {"name": "Social Science & Humanities / English", "code": "HUM", "courses": [
            {"name": "B.A. Eng / B.A. Eng (Hons./By Research)", "code": "BA_ENG"},
            {"name": "B.A. Eco / B.A. Eco (Hons./By Research)", "code": "BA_ECO"}
        ]},
        {"name": "Business Management / Commerce", "code": "MGMT", "courses": [
            {"name": "BBA / BBA (Hons./By Research)", "code": "BBA"},
            {"name": "BBA (Family Business)", "code": "BBA_FB"},
            {"name": "BBA (Management Sciences)", "code": "BBA_MS"},
            {"name": "B.Com / B.Com (Hons./By Research)", "code": "BCOM"},
            {"name": "B.Com Global Accounting in Association with CIMA", "code": "BCOM_CIMA"}
        ]},
        {"name": "Legal Studies", "code": "LAW", "courses": [
            {"name": "BBA LLB (Hons.)", "code": "BBALLB"},
            {"name": "B.A. LLB (Hons.)", "code": "BALLB"}
        ]},
        {"name": "Faculty of Education", "code": "EDU", "courses": [
            {"name": "B.Ed.", "code": "BED"}
        ]},
        {"name": "Library & Information Science", "code": "LIB", "courses": [
            {"name": "Bachelor of Library and Information Science", "code": "BLIS"}
        ]}
    ]
    
    try:
        for dept_info in department_data:
            courses = [Course(name=c['name'], code=c['code']) for c in dept_info['courses']]
            department = Department(name=dept_info['name'], code=dept_info['code'], courses=courses)
            department.save()
        return jsonify({"message": f"Seeded {len(department_data)} departments"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500