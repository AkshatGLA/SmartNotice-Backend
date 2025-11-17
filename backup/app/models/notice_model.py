from mongoengine import Document, EmbeddedDocument, EmbeddedDocumentField, StringField, DictField, ListField, DateTimeField, EmailField, IntField, BooleanField, ReferenceField
import datetime

class Notice(Document):
    title = StringField(required=True)
    subject = StringField()
    content = StringField(required=True)
    notice_type = StringField()
    departments = ListField(StringField(), default=[])
    program_course = StringField()
    specialization = StringField(default="core")
    year = StringField()
    section = StringField()
    recipient_emails = ListField(StringField(), default=[])
    priority = StringField(choices=["Normal", "Urgent", "Highly Urgent"], default="Normal")
    status = StringField(default="draft", choices=["draft", "published", "scheduled", "pending_approval"])
    send_options = DictField(default={"email": False, "web": True})
    schedule_date = BooleanField(default=False)
    schedule_time = BooleanField(default=False)
    date = StringField()
    time = StringField()
    from_field = StringField()
    publish_at = DateTimeField()
    created_at = DateTimeField(default=datetime.datetime.now)
    updated_at = DateTimeField(default=datetime.datetime.now)
    created_by = StringField(required=True)
    created_by_name = StringField()
    attachments = ListField(StringField(), default=[])
    reads = ListField(DictField(), default=[])
    read_count = IntField(default=0)
    requires_approval = BooleanField(default=False)
    approval_workflow = ListField(ReferenceField('Approval'))
    auto_publish_after_approval = BooleanField(default=False)
    current_approval_level = IntField(default=0)
    approval_status = StringField(choices=['pending', 'approved', 'rejected', 'not_required'], default='not_required')
    rejection_reason = StringField()
    
    # New fields for approval tracking
    approved_by = StringField()
    approved_by_name = StringField()
    approved_at = DateTimeField()
    approval_comments = StringField()
    
    meta = {
        'collection': 'notices',
        'indexes': [
            '-created_at',
            'created_by',
            'notice_type',
            'status',
            'departments',
            'year',
            'priority',
            'section',
            'program_course',
            'approval_status',
            'approved_by_name',
            'approved_at',
        ]
    }