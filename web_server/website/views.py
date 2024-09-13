import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import time
from shared.utils import *
from shared.constants import * 
from flask_login import login_required, current_user
from flask import Blueprint, render_template, redirect, url_for, Response, current_app

views = Blueprint('views', __name__)


@views.route('/', methods=['GET'])
def home() -> Response:
    if current_user.is_authenticated:
        return redirect(url_for('views.choose_action'))
    return redirect(url_for('views.home_view'))


@views.route('/home', methods=['GET'])
def home_view():
    return render_template('home.html', user=current_user)


@views.route('/about_us', methods=['GET'])
def about_us():
    return render_template('about_us.html', user=current_user)


@login_required
@views.route('/choose_action', methods=['GET'])
def choose_action():
    return render_template('choose_action.html', user=current_user)