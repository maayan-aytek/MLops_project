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

    if status_code >= 400:
        current_app.config['FAIL'] += 1
    else:
        current_app.config['SUCCESS'] += 1
    
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