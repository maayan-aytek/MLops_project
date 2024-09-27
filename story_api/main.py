from website.app import create_app
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import IP, STORY_API_PORT

app = create_app()

if __name__ == '__main__':
    app.run(host=IP, port=STORY_API_PORT, debug=True)
