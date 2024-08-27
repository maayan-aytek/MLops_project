from website.app import create_app, socketio
import json 

app = create_app()

if __name__ == '__main__':
    with open('./shared/secrets.json', 'r') as file:
        secrets = json.load(file)
        API_KEY = secrets['API_KEY']
        IP = secrets['IP']
        WEB_PORT = secrets['WEB_SERVER_PORT']

    socketio.run(app, debug=True, host=IP, port=WEB_PORT, use_reloader=False)