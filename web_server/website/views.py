import os 
import json
import time
import PIL.Image
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import *
from typing import Union, Optional
import google.generativeai as genai
from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, redirect, url_for, Response, current_app
import requests 
import json 
import base64

API_PORT = 8000  
API_IP = "192.168.1.21"
API_BASE_URL = f"http://{API_IP}:{API_PORT}/"


# Load API key from secrets file
with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']

# Configuring Gemini API 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Define Blueprint for views
views = Blueprint('views', __name__)

@views.route('/', methods=['GET'])
def home() -> Response:
    """
    Redirect to the login page.
    This view function redirects to the login page if accessed.
    Returns:
        Response: A redirect response to the login page.
    """
    if current_user.is_authenticated:
        return redirect(url_for('views.upload_image'))
    return redirect(url_for('auth.login'))


@views.route('/status', methods=['GET'])
def status():
    data = {
        'uptime': time.time() - current_app.config['START_TIME'],
        'processed': {
            'success': current_app.config['SUCCESS'],
            'fail': current_app.config['FAIL'],     
            'running': 0,
            'queued': 0   
        },
        'health': 'ok',
        'api_version': 0.21,
    }
    return create_json_response({'status': data}, 200)


@views.route('/upload_image', methods=['GET', 'POST'])
@login_required
def upload_image() -> Union[Response, str]:
    """
    Handle image upload and classification.
    This view handles both GET and POST requests. On a POST request, it checks
    for an uploaded image, validates its format, saves it, and classifies it
    using the Gemini API. On a GET request, it renders the upload page.
    Returns:
        Response: A JSON response with the classification result or an error message.
    """
    if request.method == 'POST':
        image = request.files['image']
        image_filename = image.filename
        method = request.form.get('method')
        if method == "sync":
            response = requests.post(API_BASE_URL + "upload_image", files={"image": (image_filename, image)})
        else:
            response = requests.post(API_BASE_URL + "async_upload", files={"image": (image_filename, image)})
            if 'request_id' in response.json():
                result = response.json()
                request_id = result['request_id']
                image.seek(0)  # Make sure to seek to the start if previously read
                image_data = image.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                current_app.config['image_dict'][str(request_id)] = base64_image

        result = response.json()

        return create_json_response(result, response.status_code)
    return render_template("index.html", user=current_user)



@views.route('/result/<request_id>', methods=['GET'])
@login_required
def get_result_with_id(request_id) -> Response:
    """
    Retrieve the result for a specific request ID.
    This view returns a 404 error if the specified request ID does not exist (always the case in our app since it is sync)
    Args:
        request_id (str): The ID of the request to retrieve the result for.
    Returns:
        Response: A JSON response 
    """
    from werkzeug.datastructures import FileStorage

    response = requests.get(API_BASE_URL + f"result/{request_id}")
    result = response.json()
    image_storage = current_app.config['image_dict'][str(request_id)]

    return render_template('result.html', request_id=request_id, result=result, current_image=image_storage)
