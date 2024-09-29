import os 
import sys
import time
import random
import PIL.Image
from io import BytesIO
import concurrent.futures
from typing import Union, Optional, Dict, Any
from flask import Blueprint, request, redirect, url_for, Response, current_app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import *
from shared.constants import MONGO_CLIENT

model = get_LLM_model()

# Define Blueprint
image_api = Blueprint('image_api', __name__)

db = MONGO_CLIENT['image_rest_api']
monitor_collection = db['monitor_health']
request_collection = db['request_track']


def classify_image(img: str) -> Optional[Dict]:
    """
    Classify an uploaded image.
    This function uses the Gemini API to classify the main object in an image.
    Args:
        image_path (str): The path to the image file.
    Returns:
        Optional[str]: The classification result, or None if classification fails.
    """
    try:
        response = model.generate_content(["What is the main object in the photo? answer just in one word- the main object", img], stream=True)
        response.resolve()
        classification = response.text


        if classification:
            return {'matches': [{'name': classification, 'score': 0.9}]}
        else:
            return None
    except Exception as e:
        return None


@image_api.route('/', methods=['GET'])
def home() -> Response:
    """
    Redirect to the login page.
    This view function redirects to the login page if accessed.
    Returns:
        Response: A redirect response to the login page.
    """
    return redirect(url_for('views.upload_image'))


@image_api.route('/status', methods=['GET'])
def status() -> Response:
    """
    :return: A JSON response with the status of the API.
    """
    montor_dict = monitor_collection.find_one()
    data = {
        'uptime': time.time() - montor_dict['start_time'],
        'processed': {
            'success': montor_dict['success'],
            'fail': montor_dict['fail'],     
            'running': montor_dict['running'],
            'queued': 0 
        },
        'health': 'ok',
        'api_version': 0.3,
    }
    return create_json_response({'status': data}, 200)


@image_api.route('/upload_image', methods=['POST'])
@monitor_status(monitor_collection)
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
            if image.read() == b'':
                return create_json_response({'error': {'code': 400, 'message': 'The uploaded image is empty'}}, 400)
            classification_result = classify_image(PIL.Image.open(image))
            if classification_result is not None:
                return create_json_response(classification_result, 200)
            else:
                return create_json_response({'error': {'code': 400, 'message': 'Classification failed'}}, 400)
        else:
            return create_json_response({'error': {'code': 400, 'message': 'No image found in request'}}, 400)


def execute_async_upload_image(image_data: bytes) -> Dict[str, Any]:
    """
    Execute async image upload and classification.
    :param image_data:
    :return: classification result
    """
    image = PIL.Image.open(BytesIO(image_data))
    classification_result = classify_image(image)
    return classification_result


def save_result_to_db(future: Any, request_id: str) -> None:
    """
    Save the classification result to the database.
    :param future: thread
    :param request_id: request id
    """
    if future.exception() is not None:
        request_collection.update_one(
        {'request_id': str(request_id)},
        {'$set': {'status': 'failed'}},
        )
    else:
        try:
            result = future.result()
            request_collection.update_one(
                {'request_id': str(request_id)},
                {'$set': {'status': 'completed', 'classification_result': result}},
            )
        except Exception as e:
            raise Exception(f"Error processing request {request_id}: {e}")


@image_api.route('/async_upload', methods=['POST'])
@monitor_status(monitor_collection)
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
    if image_data == b'':
        return create_json_response({'error': {'code': 400, 'message': 'The uploaded image is empty'}}, 400)

    request_id = random.randint(10000, 1000000)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(execute_async_upload_image, image_data)
        request_collection.insert_one(
            {'request_id': str(request_id), 'status': 'pending'},
        )
        future.add_done_callback(lambda fut: save_result_to_db(fut, request_id))
        time.sleep(1)
    return create_json_response({'request_id': request_id}, 202)


@image_api.route('/result/<request_id>', methods=['GET'])
def get_result_with_id(request_id: str) -> Response:
    """
    Retrieve the result for a specific request ID.
    This view returns a 404 error if the specified request ID does not exist.
    
    Args:
        request_id (str): The ID of the request to retrieve the result for.
    Returns:
        Response: A JSON response with the classification result or the current status.
    """
    request_data = request_collection.find_one({'request_id': request_id})
    
    if not request_data:
        return create_json_response({'error': {'code': 404, 'message': 'ID not found'}}, 404)

    status = request_data.get('status')

    if status == 'pending':
        return create_json_response({'status': 'running'}, 200)
    
    elif status == 'completed':
        classification_result = request_data['classification_result']
        classification_result.update({'status': "completed"})
        return create_json_response(classification_result, 200)

    elif status == 'failed':
        return create_json_response({'error': {'code': 400, 'message': 'Classification failed'}, 'status': 'error'}, 200)

    else:
        return create_json_response({'error': {'code': 400, 'message': 'Unknown error or unhandled exception'}}, 400)