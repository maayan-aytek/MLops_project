import time
from flask import Flask
from .story_api import story_api


def create_app() -> Flask:
    """
    Create and configure the Flask application.
    This function sets up the Flask app with necessary configurations, 
    initializes the database, and registers blueprints for the application.
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'secret key'
    app.config['SUCCESS'] = 0
    app.config['FAIL'] = 0
    app.config['START_TIME'] = time.time()
    app.config['process_dict'] = {}
    
    app.register_blueprint(story_api, url_prefix='/')

    return app