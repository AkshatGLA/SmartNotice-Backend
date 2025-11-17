# models/notification_model.py
from datetime import datetime
from mongoengine import Document, StringField, DateTimeField, BooleanField, URLField

class Notification(Document):
    user_id = StringField(required=True)  # ID of the user to receive the notification
    title = StringField(required=True)
    message = StringField(required=True)
    notification_type = StringField(choices=[
        'notice', 
        'alert', 
        'reminder', 
        'announcement'
    ], default='notice')
    action_url = URLField()  # URL to navigate when notification is clicked
    is_read = BooleanField(default=False)
    created_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'notifications',
        'indexes': [
            'user_id',
            'is_read',
            '-created_at',
            {'fields': ['user_id', 'is_read']}
        ]
    }
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'title': self.title,
            'message': self.message,
            'type': self.notification_type,
            'action_url': self.action_url,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat()
        }