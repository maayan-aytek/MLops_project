import os
from website.app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(host='10.0.0.5', port=8000, debug=True)
