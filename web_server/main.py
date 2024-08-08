from website.app import create_app
from flask_socketio import SocketIO, join_room, leave_room, send
from website.views import socketio

app, socketio = create_app()

if __name__ == '__main__':
    # app.run(host='192.168.1.21', port=5000, debug=True)
    socketio.run(app, debug=True)
    # socketio.run(app, debug=True, host='0.0.0.0', port=5050, use_reloader=False, async_mode='eventlet')
    # socketio.run(app, debug=True, host='0.0.0.0', port=5050, use_reloader=False, async_mode='eventlet')


