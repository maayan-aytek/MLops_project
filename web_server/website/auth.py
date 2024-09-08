from .models import User
from typing import Union, Optional
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import create_json_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response, current_app

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['GET', 'POST'])
def login() -> Union[Response, str]:
    """
    Handle user login.
    This route handles both GET and POST requests for user login. It checks 
    the request type (form or JSON), validates user credentials, and logs in 
    the user if credentials are correct. 
    Returns:
        Union[Response, str]: A JSON response for API requests or a redirect/rendered HTML for web requests.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        # check if the user already login
        if current_user.is_authenticated:
            flash('The user already logged in.')
            return create_json_response({'error': {'code': 401, 'message': 'The user already login.'}}, 401)

        db = current_app.config['MONGO_DB']
        user = db.find_one({"username": username})
        if user and check_password_hash(user['password'], password):
            flash('Logged in successfully!', category='success')
            login_user(User(user), remember=True)
            return redirect(url_for('views.choose_action'))
        else:
            flash('Incorrect username or password.', category='error')
            return create_json_response({'error': {'code': 401, 'message': 'Incorrect username or password.'}}, 401)
        
    return render_template("login.html", user=current_user)
    

@auth.route('/logout')
@login_required
def logout() -> Response:
    """
    Logs out the currently authenticated user.
    Returns:
        Response: A redirect response to the login page.
    """
    logout_user()
    return redirect(url_for('auth.login'))


def check_strong_password(password):
    if not any(c.isupper() for c in password) or \
       not any(c.islower() for c in password) or \
       not any(c.isdigit() for c in password):
    
        return False, "Password should contain at least one Upper case letters: A-Z, one Lowercase letters: a-z, and one Number: 0-9."
    return True, "True"


@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up() -> Union[Response, str]:
    """
    This route handles both GET and POST requests for user sign-up. 
    creates a new user if the validation passes, and logs in the new user. 
    Returns:
        Union[Response, str]: A JSON response for API requests or a redirect/rendered HTML for web requests.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        first_name = request.form.get('name')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        message = ''
        is_password_strong, password_message = check_strong_password(password1)
        db = current_app.config['MONGO_DB']
        user = db.find_one({"username": username})
        if user:
            flash('Username already exists.', category='error')
            message = 'Username already exists.'
        elif len(username) < 1:
            flash('Username must be not empty.', category='error')
            message = 'Username must be not empty.'
        elif len(first_name) < 1:
            flash('First name must be not empty.', category='error')
            message = 'First name must be not empty.'
        elif not is_password_strong:
            flash(password_message, category='error')
            message = password_message
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
            message = 'Passwords don\'t match.'
        elif len(password1) < 1:
            flash('Password must be not empty.', category='error')
            message = 'Password must be not empty.'
        else:
            new_user = {
                "username": username,
                "first_name": first_name,
                "password": generate_password_hash(password1, method='pbkdf2:sha256')
            }
            db.insert_one(new_user)
            login_user(User(new_user), remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.choose_action'))

        if message != '':
            return create_json_response({'error': {'code': 401, 'message': message}}, 401)
    return render_template("sign_up.html", user=current_user)