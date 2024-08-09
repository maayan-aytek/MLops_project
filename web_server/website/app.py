import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import time
from flask import Flask
from typing import Dict, Any
from flask_pymongo import PyMongo
from pymongo import MongoClient
from flask_socketio import SocketIO
from flask_login import LoginManager, current_user
socketio = SocketIO()

def create_app() -> Flask:
    from .auth import auth
    from .views import views
    from .models import User
    from .database import init_db
    from shared.utils import create_json_response

    """
    Create and configure the Flask application.
    This function sets up the Flask app with necessary configurations, 
    initializes the database, and registers blueprints for the application.
    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'super-secret'
    app.config['SUCCESS'] = 0
    app.config['FAIL'] = 0
    app.config['START_TIME'] = time.time()
    app.config['image_dict'] = {}
    client = MongoClient('mongodb://10.0.0.5:27017/')
    db = client['customtales']
    users_collection = db['users']
    app.config['MONGO_CLIENT'] = client
    app.config['MONGO_DB'] = users_collection
    
    socketio.init_app(app)  

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @app.context_processor
    def inject_user() -> Dict:
        """
        Inject the current user into the template context.
        Returns:
            Dict: A dictionary containing the current user.
        """
        return dict(user=current_user)

    @login_manager.user_loader
    def load_user(username):
        u = users_collection.find_one({"username": username})
        if not u:
            return None
        return User(u)

    @login_manager.unauthorized_handler
    def unauthorized_callback() -> Any:
        """
        Handle unauthorized access attempts.
        This function provides a response based on the content type of the request,
        returning a JSON response for API requests
        Returns:
            Any: A JSON response 
        """
        return create_json_response({'error': {'code': 401, 'message': 'You unatuhorized access that page, please log in.'}},401)
    return app