import os
import time
from .auth import auth
from .models import User
from .views import views
from typing import Dict, Any
from .database import db, init_db
from utils import create_json_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user
from flask import Flask, request, flash, redirect, url_for


DB_NAME = "database.db"

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
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
    init_db(app)

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
    def load_user(id: int) -> User:
        """
        Load a user by their ID.
        Args:
            id (int): The user's ID.
        Returns:
            User: The user instance corresponding to the provided ID.
        """
        return User.query.get(int(id))

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