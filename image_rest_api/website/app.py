import time
from .views import views
from flask_login import LoginManager
from flask import Flask


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

    app.register_blueprint(views, url_prefix='/')

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)
    return app