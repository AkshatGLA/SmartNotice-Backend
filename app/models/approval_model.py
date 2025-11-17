from mongoengine import Document, ReferenceField, StringField, DateTimeField
from datetime import datetime

class Approval(Document):
    notice_id = ReferenceField('Notice', required=True)
    approver_id = StringField(required=True)
    approver_name = StringField(required=True)
    approver_role = StringField(required=True)
    approver_department = StringField()
    status = StringField(required=True, choices=['pending', 'approved', 'rejected'], default='pending')
    comments = StringField()
    signature = StringField()
    approved_by_name = StringField()
    approved_by_role = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    approved_at = DateTimeField()
    
    meta = {
        'collection': 'approvals',
        'indexes': [
            'notice_id',
            'approver_id',
            'status',
            'created_at'
        ]
    }