from website.app import create_app
import json

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    IP = secrets['IP']
    STORY_API_PORT = secrets['STORY_API_PORT']

app = create_app()

if __name__ == '__main__':
    app.run(host=IP, port=STORY_API_PORT, debug=True)
