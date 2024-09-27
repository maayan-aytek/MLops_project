from website.app import create_app, socketio
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import IP, WEB_SERVER_PORT

app = create_app()

if __name__ == '__main__':
    socketio.run(app, debug=True, host=IP, port=WEB_SERVER_PORT, use_reloader=False, allow_unsafe_werkzeug=True)