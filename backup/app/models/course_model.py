from mongoengine import  EmbeddedDocument,StringField



class Course(EmbeddedDocument):
    name = StringField(required=True)
    code = StringField(required=True, unique=True)
