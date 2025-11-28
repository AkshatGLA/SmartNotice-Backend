# # from flask import Flask
# # from flask_cors import CORS
# # import os
# # from dotenv import load_dotenv
# # from mongoengine import connect
# # from pymongo.errors import ConnectionFailure

# # # Load environment variables
# # load_dotenv()
# # PORT = os.environ.get('PORT', 5001)

# # def create_app():
# #     app = Flask(__name__)
    
# #     # Configuration (identical to original)
# #     app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6k')

# #     # CORS (identical to original)
# #     CORS(app, resources={
# #         r"/api/*": {
# #             "origins": ["http://localhost:5001","*"],
# #             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
# #             "allow_headers": ["Authorization", "Content-Type"],
# #             "supports_credentials": True
# #         }
# #     })

# #     # Database Connection (identical to original)
# #     MONGO_URI = os.environ.get('MONGO_URI')
# #     try:
# #         connect(db="smart-notice", host=MONGO_URI)
# #         print("✅ MongoDB Connected Successfully!")
# #     except ConnectionFailure as e:
# #         print("❌ MongoDB Connection Failed:", str(e))

# #     # Import and register blueprints
# #     from app.controllers.auth_controllers import auth_bp
# #     from app.controllers.notices_controller import notice_bp
# #     # from app.controllers.student_controllers import student_bp
# #     from app.controllers.department_controllers import department_bp
# #     from app.controllers.user_controllers import user_bp
# #     from app.controllers.university_controllers import university_bp
# #     from app.controllers.student_profile_controller import profile_bp
# #     from app.controllers.digitalSignature import digital_signature_bp
# #     from app.controllers.holidayAutomation import holiday_api
# #     # from app.controllers.notification_controller import notification_bp

# #     from app.controllers.employee_controller import employee_bp
# #     from app.controllers.approval_controller import approval_bp
# #     # from app.controllers.classification_controller import classification_bp
# #     # from app.controllers.data_upload_controllers import upload_bp
# #     # from app.controllers.digitalSignature import digital_signature_bp
# #     # from app.controllers.approval_controllers import approval_bp

# #     from app.controllers.holidayAutomation import holiday_api, start_holiday_checker
# #     start_holiday_checker()
# #     app.register_blueprint(holiday_api)



# #     app.register_blueprint(auth_bp)
# #     app.register_blueprint(notice_bp)
# #     # app.register_blueprint(student_bp)
# #     app.register_blueprint(department_bp)
# #     app.register_blueprint(user_bp)
# #     app.register_blueprint(university_bp)
# #     app.register_blueprint(profile_bp)
# #     app.register_blueprint(digital_signature_bp)
# #     app.register_blueprint(employee_bp)
# #     app.register_blueprint(approval_bp)
# #     # app.register_blueprint(classification_bp)
# #     # app.register_blueprint(upload_bp)
# #     # app.register_blueprint(holiday_api)
# #     # app.register_blueprint(digital_signature_bp)

# #     # app.register_blueprint(notification_bp)

# #     @app.route("/")
# #     def hello():
# #         return "WELCOME TO AWS BACKEND"

# #     return app

# # if __name__ == "__main__":
# #     app = create_app()
# #     app.run(debug=True, port=PORT)















from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import os
from dotenv import load_dotenv
from mongoengine import connect
from pymongo.errors import ConnectionFailure

# Load environment variables
load_dotenv()
PORT = os.environ.get('PORT', 5001)

# ✅ SocketIO initialized globally with proper configuration
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='threading',  # Add this for better compatibility
    logger=True,            # Enable logging
    engineio_logger=True    # Enable engineio logging
)

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6k')

    # CORS setup
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "*"],  # React frontend port
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
    def hello():
        return "WELCOME TO AWS BACKEND"

    # ✅ Attach SocketIO to Flask
    socketio.init_app(app)

    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    print(f"🚀 Starting Flask-SocketIO server on port {PORT}...")
    print(f"📡 SocketIO CORS enabled for all origins")
    print(f"🔗 WebSocket server will be available at: http://localhost:{PORT}")
    socketio.run(app,
             debug=False,
             port=PORT,
             host='0.0.0.0',
             use_reloader=False,
             allow_unsafe_werkzeug=True)














# from app import create_app
# from app.extensions import socketio

# app = create_app()

# if __name__ == "__main__":
#     print(f"🚀 Starting Flask-SocketIO server on port {app.config.get('PORT', 5001)}...")
#     print(f"📡 SocketIO CORS enabled for all origins")
#     print(f"🔗 WebSocket server will be available at: http://localhost:{app.config.get('PORT', 5001)}")
    
#     # Run with socketio instead of app.run()
#     socketio.run(
#         app, 
#         debug=True, 
#         port=app.config.get('PORT', 5001), 
#         host='0.0.0.0',
#         allow_unsafe_werkzeug=True
#     )