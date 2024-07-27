from .models import User
from .database import db
from typing import Union, Optional
from utils import create_json_response
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, login_required, logout_user, current_user
from flask import Blueprint, render_template, request, flash, redirect, url_for, Response

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

        user = User.query.filter_by(username=username).first()
        if user:
            if check_password_hash(user.password, password):
                flash('Logged in successfully!', category='success')
                login_user(user, remember=True)
                return redirect(url_for('views.upload_image'))
            else:
                flash('Incorrect password, try again.', category='error')
                return create_json_response({'error': {'code': 401, 'message': 'Incorrect password.'}}, 401)
        else:
            flash('Username does not exist.', category='error')
            return create_json_response({'error': {'code': 401, 'message': 'Username does not exist.'}}, 401)

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
        first_name = request.form.get('firstName')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        message = ''
        user = User.query.filter_by(username=username).first()
        if user:
            flash('Username already exists.', category='error')
            message = 'Username already exists.'
        elif len(username) < 1:
            flash('Username must be not empty.', category='error')
            message = 'Username must be not empty.'
        elif len(first_name) < 1:
            flash('First name must be not empty.', category='error')
            message = 'First name must be not empty.'
        elif password1 != password2:
            flash('Passwords don\'t match.', category='error')
            message = 'Passwords don\'t match.'
        elif len(password1) < 1:
            flash('Password must be not empty.', category='error')
            message = 'Password must be not empty.'
        else:
            new_user = User(username=username, first_name=first_name, password=generate_password_hash(password1, method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')
            return redirect(url_for('views.upload_image'))

        if message != '':
            return create_json_response({'error': {'code': 401, 'message': message}}, 401)
    return render_template("sign_up.html", user=current_user)
