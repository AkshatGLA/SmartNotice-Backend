# # app/__init__.py or your main application file
# from flask import Flask
# from .extensions import socketio

# def create_app():
#     app = Flask(__name__)
    
#     # Other configurations...
    
#     # Initialize SocketIO with the app
#     socketio.init_app(app)
    
#     return app, socketio



from flask import Flask
app = Flask(__name__)