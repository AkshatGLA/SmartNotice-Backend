from mongoengine import  EmbeddedDocument,StringField,Document,ListField,EmbeddedDocumentField
from ..models.course_model import Course




class Department(Document):
    name = StringField(required=True, unique=True)
    code = StringField(required=True, unique=True)
    courses = ListField(EmbeddedDocumentField(Course))

    meta = {'collection': 'departments'}