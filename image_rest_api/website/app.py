import time
from flask import Flask
from .image_api import image_api
from shared.constants import MONGO_CLIENT


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
    app.config['process_dict'] = {}

    db = MONGO_CLIENT['image_rest_api']
    monitor_collection = db['monitor_health']
    request_collection = db['request_track']
    request_collection.delete_many({})
    monitor_collection.delete_many({})
    initial_info = {
                'success': 0,
                'fail': 0,     
                'running': 0,
                'queued': 0,
                'start_time': time.time()
            }
    monitor_collection.insert_one(initial_info)

    app.register_blueprint(image_api, url_prefix='/')

    return app