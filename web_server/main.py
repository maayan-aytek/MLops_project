from website.app import create_app
import json 

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    IP = secrets['IP']
    WEB_SERVER_PORT = secrets['WEB_SERVER_PORT']


app = create_app()

if __name__ == '__main__':
    app.run(host=IP, port=WEB_SERVER_PORT, debug=True)
