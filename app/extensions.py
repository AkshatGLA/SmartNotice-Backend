# # app/extensions.py
# from flask_socketio import SocketIO

# # Initialize SocketIO globally
# socketio = SocketIO(
#     cors_allowed_origins="*", 
#     async_mode='threading',
#     logger=True,
#     engineio_logger=True
# )
# app/extensions.py


from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')