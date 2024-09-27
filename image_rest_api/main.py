from website.app import create_app
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import IMAGE_API_PORT, IP


app = create_app()

if __name__ == '__main__':
    app.run(host=IP, port=IMAGE_API_PORT, debug=True)
