import os
import eventlet
eventlet.monkey_patch()     # IMPORTANT for WebSockets

from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
from dotenv import load_dotenv
from mongoengine import connect
from pymongo.errors import ConnectionFailure

# Load environment variables
load_dotenv()
PORT = int(os.environ.get('PORT', 5001))

# SocketIO (eventlet async mode)
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="eventlet",
    logger=False,
    engineio_logger=False
)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get(
        'SECRET_KEY',
        'supersecret123'
    )

    # CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*", "http://localhost:5173"],
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
        print("❌ MongoDB Connection Failed:", e)

    # Import & register blueprints
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

    start_holiday_checker()

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
    def home():
        return "SmartNotice Backend Running Successfully!"

    socketio.init_app(app)
    return app


app = create_app()

if __name__ == "__main__":
    print(f"🚀 Running backend on port {PORT}")
    print("🔗 WebSockets enabled (eventlet mode)")
    socketio.run(app, host="0.0.0.0", port=PORT, debug=False)
