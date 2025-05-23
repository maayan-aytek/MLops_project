import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import base64
import requests
from typing import Union
from shared.utils import *
from shared.constants import * 
from flask_login import login_required, current_user
from flask import Blueprint, render_template, request, Response, current_app

image_classification = Blueprint('image_classification', __name__)

logger = get_logger()

@image_classification.route('/classify_image', methods=['GET', 'POST'])
@login_required
def classify_image() -> Union[Response, str]:
    """
    Classify image route
    :return: Response object or rendered template
    """
    if request.method == 'POST':
        image = request.files['image']
        image_filename = image.filename
        method = request.form.get('method')

        if method == "sync":
            response = requests.post(IMAGE_API_BASE_URL + "upload_image", files={"image": (image_filename, image)})
        else:
            response = requests.post(IMAGE_API_BASE_URL + "async_upload", files={"image": (image_filename, image)})
            if 'request_id' in response.json():
                result = response.json()
                request_id = result['request_id']
                image.seek(0)
                image_data = image.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                current_app.config['image_dict'][str(request_id)] = base64_image

        result = response.json()

        return create_json_response(result, response.status_code)
    return render_template("index.html", user=current_user)


@image_classification.route('/result/<request_id>', methods=['GET', 'POST'])
@login_required
def get_result_with_id(request_id) -> Response:
    """
    Get result with request id
    :param request_id: Request id of the image
    :return: Response object or rendered template
    """
    if str(request_id) not in current_app.config['image_dict']:
        return create_json_response({'error': {'code': 404, 'message': f"Invalid request id: {request_id}"}},404)
    
    response = requests.get(IMAGE_API_BASE_URL + f"result/{request_id}")
    result = response.json()
    image_storage = current_app.config['image_dict'][str(request_id)]
    
    if request.method == 'POST':
        return create_json_response(result, response.status_code)
    return render_template('result.html', request_id=request_id, result=result, current_image=image_storage)