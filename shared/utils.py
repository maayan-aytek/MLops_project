from flask import jsonify, Response, current_app
from typing import List, Dict, Union


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

