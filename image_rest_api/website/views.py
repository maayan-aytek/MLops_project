import os 
from io import BytesIO
import json
import time
import PIL.Image
import sys
import concurrent.futures
import random
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import *
from typing import Union, Optional
import google.generativeai as genai
from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, Response, current_app


# Load API key from secrets file
with open(os.path.join('shared', 'secrets.json'), 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']

# Configuring Gemini API 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')


# Define Blueprint for views
views = Blueprint('views', __name__)

def classify_image(img: str) -> Optional[str]:
    """
    Classify an uploaded image.
    This function uses the Gemini API to classify the main object in an image.
    Args:
        image_path (str): The path to the image file.
    Returns:
        Optional[str]: The classification result, or None if classification fails.
    """
    response = model.generate_content(["What is the main object in the photo? answer just in one word- the main object", img], stream=True)
    response.resolve()
    classification = response.text
    if classification:
        return {'matches': [{'name': classification, 'score': 0.9}]}
    return None

@views.route('/', methods=['GET'])
def home() -> Response:
    """
    Redirect to the login page.
    This view function redirects to the login page if accessed.
    Returns:
        Response: A redirect response to the login page.
    """
    return redirect(url_for('views.upload_image'))


@views.route('/status', methods=['GET'])
def status():
    running = 0
    for process in current_app.config['process_dict'].values():
        if not process.done():
            running += 1

    data = {
        'uptime': time.time() - current_app.config['START_TIME'],
        'processed': {
            'success': current_app.config['SUCCESS'],
            'fail': current_app.config['FAIL'],     
            'running': running,
            'queued': 0   
        },
        'health': 'ok',
        'api_version': 0.3,
    }
    return create_json_response({'status': data}, 200)


@views.route('/upload_image', methods=['POST'])
def upload_image() -> Union[Response, str]:
    """
    Handle sync image upload and classification.
    This view handles  POST requests. On a POST request, it checks
    for an uploaded image, validates its format, saves it, and classifies it
    using the Gemini API. 
    Returns:
        Response: A JSON response with the classification result or an error message.
    """
    if request.method == 'POST': 
        if 'image' in request.files:
            image = request.files['image']
            if '.' not in image.filename:
                return create_json_response({'error': {'code': 400, 'message': "The filename invalid"}},400)
            if image.filename.split('.')[0] == '':
                return create_json_response({'error': {'code': 400, 'message': "The filename empty"}},400)
            if image.filename.split('.')[1].lower() not in ['png', 'jpg', 'jpeg']: # Unsupported file
                return create_json_response({'error': {'code': 400, 'message': "Support image in format ['png', 'jpg', 'jpeg']"}}, 400)
            classification_result = classify_image(PIL.Image.open(image))
            if classification_result is not None:
                return create_json_response(classification_result, 200)
            else:
                return create_json_response({'error': {'code': 401, 'message': 'Classification failed'}}, 401)
        else:
            return create_json_response({'error': {'code': 400, 'message': 'No image found in request'}}, 400)
        

def execute_async_upload_image(image_data):
    image = PIL.Image.open(BytesIO(image_data))
    classification_result = classify_image(image)
    return classification_result

@views.route('/async_upload', methods=['POST'])
def async_upload() -> Union[Response, str]:
    """
    Handle async image upload and classification.
    This view handles both GET and POST requests. On a POST request, it checks
    for an uploaded image, validates its format, saves it, and classifies it
    using the Gemini API.
    Returns:
        Response: A JSON response with the classification result or an error message.
    """
    if 'image' not in request.files:
        return create_json_response({'error': {'code': 400, 'message': 'No image found in request'}}, 400)
    
    image = request.files['image']
    if '.' not in image.filename or image.filename.split('.')[1].lower() not in ['png', 'jpg', 'jpeg']:
        return create_json_response({'error': {'code': 400, 'message': "Support image in format ['png', 'jpg', 'jpeg']"}}, 400)
    image_data = image.read() 

    request_id = random.randint(10000, 1000000)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(execute_async_upload_image, image_data)
        current_app.config['process_dict'][str(request_id)] = future
        time.sleep(1)
    return create_json_response({'request_id': request_id}, 202)



@views.route('/result/<request_id>', methods=['GET'])
def get_result_with_id(request_id) -> Response:
    """
    Retrieve the result for a specific request ID.
    This view returns a 404 error if the specified request ID does not exist (always the case in our app since it is sync)
    Args:
        request_id (str): The ID of the request to retrieve the result for.
    Returns:
        Response: A JSON response 
    """
    if request_id not in current_app.config['process_dict']:
        return create_json_response({'error': {'code': 404, 'message': 'ID not found'}}, 404)
    future = current_app.config['process_dict'][request_id]
    if future.done():
        if future.exception() is not None:
            return {}
        else:
            classification_result = future.result()
            if classification_result is not None:
                create_json_response(classification_result, 200)
                classification_result.update({'status': "completed"})
            else:
                classification_result = {'error': {'code': 401, 'message': 'Classification failed'}}
                create_json_response(classification_result, 401)
                classification_result.update({'status': "failed"})
            return create_json_response(classification_result, 200)
    else:
        return create_json_response({'status': "running"}, 200)
    