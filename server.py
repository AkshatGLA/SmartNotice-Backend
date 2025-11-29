# -------------------------------------------------------------------------
# CRITICAL: Monkey patch must happen BEFORE importing other libraries
# -------------------------------------------------------------------------
import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_cors import CORS
import os
from dotenv import load_dotenv
from mongoengine import connect
from pymongo.errors import ConnectionFailure
from app.extensions import socketio

# Load environment variables
load_dotenv()
PORT = int(os.environ.get('PORT', 5001))

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9')

    # ✅ CORS FIX
    # 1. Removed "*" (It breaks requests when supports_credentials=True)
    # 2. Added your deployed domain explicitely
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173", 
                "https://smartnoticesystem.duckdns.org",
                "https://akshat.devai.in"
            ],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Authorization", "Content-Type"],
            "supports_credentials": True
        }
    })

    # DB connection
    MONGO_URI = os.environ.get('MONGO_URI')
    try:
        connect(db="smart-notice", host=MONGO_URI)
        print("✅ MongoDB Connected Successfully!")
    except ConnectionFailure as e:
        print("❌ MongoDB Connection Failed:", str(e))

    # Register blueprints
    from app.controllers.auth_controllers import auth_bp
    from app.controllers.notices_controller import notice_bp
    from app.controllers.department_controllers import department_bp
    from app.controllers.user_controllers import user_bp
    from app.controllers.university_controllers import university_bp
    from app.controllers.student_profile_controller import profile_bp
    from app.controllers.digitalSignature import digital_signature_bp
    from app.controllers.holidayAutomation import holiday_api, start_holiday_checker
    from app.controllers.employee_controller import employee_bp
    from app.controllers.approval_controller import approval_bp
    from app.controllers.data_upload_controllers import data_upload_bp

    # Start background tasks
    try:
        start_holiday_checker()
    except Exception as e:
        print(f"Warning: Holiday checker failed to start: {e}")

    app.register_blueprint(holiday_api)
    app.register_blueprint(auth_bp)
    app.register_blueprint(notice_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(university_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(digital_signature_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(approval_bp)
    app.register_blueprint(data_upload_bp)

    @app.route("/")
    def hello():
        return "WELCOME TO SMART NOTICE BACKEND"

    socketio.init_app(app)

    return app

app = create_app()

if __name__ == "__main__":
    print(f"🚀 Starting Flask-SocketIO server on port {PORT}...")
    socketio.run(app,
             debug=True,       
             port=PORT,
             host='0.0.0.0',
             use_reloader=False)