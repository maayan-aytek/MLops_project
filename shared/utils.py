import os
import json
import random
from string import ascii_uppercase
import google.generativeai as genai
from typing import List, Dict, Union
from flask import jsonify, Response, current_app

MODEL = None


def create_json_response(data: Union[List, Dict], status_code: int) -> Response:
    """
    Creates a JSON response with a specified status code.
    
    This function takes a dictionary or a list as data and an integer as the status code,
    then returns a Flask JSON response object with the appropriate headers set.

    Args:
        data (dict or list): The data to be included in the JSON response.
        status_code (int): The HTTP status code for the response.

    Returns:
        response (Response): The Flask response object with the JSON data and headers.
    """
    response = jsonify(data)
    response.status_code = status_code
    response.headers['Content-Type'] = 'application/json'
    return response


def get_LLM_model():
    global MODEL
    if MODEL is None:
        # Load API key from secrets file
        with open(os.path.join('shared', 'secrets.json'), 'r') as file:
            secrets = json.load(file)
            API_KEY = secrets['API_KEY']

        # Configuring Gemini API 
        genai.configure(api_key=API_KEY)
        MODEL = genai.GenerativeModel('gemini-1.5-flash')

    return MODEL


def generate_unique_code(length, rooms):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code


def update_monitor_status(db, success_inc=0, fail_inc=0, running_inc=0, queued_inc=0):
    db.update_one(
        {},
        {'$inc': {
            'success': success_inc,
            'fail': fail_inc,
            'running': running_inc,
            'queued': queued_inc
        }}
    )


def monitor_status(db):
    def decorator_status(func):
        def wrapper(*args, **kwargs):
            update_monitor_status(db, running_inc=1)
            json_response = func(*args, **kwargs)
            status_code = json_response.status_code
            if status_code >= 400:
                update_monitor_status(db, fail_inc=1, running_inc=-1)
            else:
                update_monitor_status(db, success_inc=1, running_inc=-1)
            return json_response
        
        wrapper.__name__ = func.__name__
        return wrapper
    
    return decorator_status