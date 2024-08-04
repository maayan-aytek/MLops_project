import os
from website.app import create_app
import json

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    IP = secrets['IP']
    API_PORT = secrets['API_PORT']

app = create_app()

if __name__ == '__main__':
    app.run(host=IP, port=API_PORT, debug=True)
