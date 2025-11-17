from mongoengine import connect, Document, EmbeddedDocument, EmbeddedDocumentField, StringField, DictField, ListField, DateTimeField, EmailField, IntField, BooleanField, ReferenceField
import datetime

class Student(Document):
    # Identification
    class_roll_no = StringField()
    univ_roll_no = StringField(required=True, unique=True)
    course = StringField(required=True)  # e.g., B.Tech, M.Tech
    branch = StringField(required=True)  # e.g., Computer Science
    year = StringField()                 # <<-- ADD THIS LINE
    section = StringField()              # <<-- ADD THIS LINE
    
    # Personal Information
    name = StringField(required=True)
    name_hindi = StringField()
    father_name = StringField()
    mother_name = StringField()
    dob = DateTimeField()
    gender = StringField()
    address = StringField()
    
    # Contact Information
    student_mobile = StringField()
    student_alt_contact = StringField()
    father_mobile = StringField()
    father_alt_contact = StringField()
    mother_contact = StringField()
    official_email = EmailField(unique=True, sparse=True)
    
    # Academic History
    file_no = StringField()
    high_school = DictField()
    intermediate = DictField()
    graduation = DictField()
    
    # Additional Information
    lib_code = StringField()
    last_medium = StringField()
    admission_office = StringField()
    target_company = StringField()
    hobbies = StringField()
    
    # Ratings
    ratings = DictField()
    
    # System Fields
    email = EmailField(unique=True, sparse=True) # Added sparse=True to allow multiple nulls if email is missing
    password = StringField(required=True)
    raw_password = StringField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    notices = ListField(ReferenceField('Notice'))
    
    meta = {
        'collection': 'students',
        'indexes': [
            'univ_roll_no',
            'course',
            'branch',
            'year', # <<-- ADD THIS
            'section', # <<-- ADD THIS
            'email',
            'official_email',
            {'fields': ['notices'], 'sparse': True}
        ]
    }
    
    def to_profile_dict(self):
        """Convert student document to a profile dictionary"""
        profile_data = {
            "id": str(self.id),
            "univ_roll_no": self.univ_roll_no,
            "class_roll_no": self.class_roll_no,
            "name": self.name,
            "name_hindi": self.name_hindi,
            "email": self.email,
            "official_email": self.official_email,
            "course": self.course,
            "branch": self.branch,
            "year": self.year,
            "section": self.section,
            "dob": self.dob.isoformat() if self.dob else None,
            "gender": self.gender,
            "address": self.address,
            "student_mobile": self.student_mobile,
            "student_alt_contact": self.student_alt_contact,
            "father_name": self.father_name,
            "father_mobile": self.father_mobile,
            "father_alt_contact": self.father_alt_contact,
            "mother_name": self.mother_name,
            "mother_contact": self.mother_contact,
            "high_school": self.high_school or {},
            "intermediate": self.intermediate or {},
            "graduation": self.graduation or {},
            "lib_code": self.lib_code,
            "last_medium": self.last_medium,
            "admission_office": self.admission_office,
            "target_company": self.target_company,
            "hobbies": self.hobbies,
            "ratings": self.ratings or {},
            "created_at": self.created_at.isoformat(),
            "notices": []
        }
        
        # Convert Notice references to simple IDs
        if self.notices:
            profile_data["notices"] = [str(notice.id) for notice in self.notices]
        
        return profile_data

    @classmethod
    def get_student_profile(cls, student_id):
        """Get complete student profile by ID"""
        return cls.objects(id=student_id).exclude('password', 'raw_password').first()

    @classmethod
    def update_student_profile(cls, student_id, update_data):
        """Update student profile data"""
        student = cls.objects(id=student_id).first()
        if not student:
            return None
        
        for field, value in update_data.items():
            if hasattr(student, field) and field not in ['id', 'univ_roll_no', 'created_at']:
                setattr(student, field, value)
        
        student.save()
        return student