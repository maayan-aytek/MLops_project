import textwrap
import time
from flask import jsonify, Response, current_app
from typing import List, Dict, Union
from IPython.display import Markdown


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


def to_markdown(text: str) -> Markdown:
  """
    Converts text to Markdown format.
    
    This function replaces bullet points with Markdown-compatible asterisks and
    adds block quote formatting.

    Args:
        text (str): The text to be converted to Markdown.

    Returns:
        Markdown: The formatted Markdown text.
    """
  text = text.replace('•', '  *')
  return Markdown(textwrap.indent(text, '> ', predicate=lambda _: True))