import os
import time
from .views import views
from typing import Dict, Any
from shared.database import db, init_db
from shared.utils import create_json_response
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
    app.config['process_dict'] = {}
    DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
    init_db(app)

    app.register_blueprint(views, url_prefix='/')

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    return app