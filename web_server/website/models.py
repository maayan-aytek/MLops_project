from .database import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    """
    User model for storing user information.
    This class defines the user model for the application. It includes fields
    for the user's ID, username, password, and first name. 
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True)
    password = db.Column(db.String(150))
    first_name = db.Column(db.String(150))
