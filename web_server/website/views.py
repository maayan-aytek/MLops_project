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
from flask_socketio import emit, join_room, leave_room, send
import requests
import json
import base64


API_PORT = 8000  
API_IP = "192.168.1.21"
API_BASE_URL = f"http://{API_IP}:{API_PORT}/"

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

views = Blueprint('views', __name__)

@views.route('/', methods=['GET'])
def home() -> Response:
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
                image.seek(0)
                image_data = image.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
                current_app.config['image_dict'][str(request_id)] = base64_image

        result = response.json()
        return create_json_response(result, response.status_code)
    return render_template("index.html", user=current_user)

@views.route('/result/<request_id>', methods=['GET'])
@login_required
def get_result_with_id(request_id) -> Response:
    response = requests.get(API_BASE_URL + f"result/{request_id}")
    result = response.json()
    image_storage = current_app.config['image_dict'][str(request_id)]

    return render_template('result.html', request_id=request_id, result=result, current_image=image_storage)

@views.route('/create_room')
def create_room():
    return render_template('create_room.html')

@socketio.on('create_room')
def handle_create_room(data):
    room = data['room']
    print(room)
    # Emit the room_created event with broadcast=True
    emit('room_created', {'room': room}, broadcast=True)

@socketio.on('join')
def handle_join(data):
    username = data['username']
    room = data['room']
    join_room(room)
    # Emit the joined_room event with broadcast=True
    emit('joined_room', {'username': username, 'room': room}, broadcast=True)

@socketio.on('leave')
def handle_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room)
    # Emit the left_room event with broadcast=True
    emit('left_room', {'username': username, 'room': room}, broadcast=True)

@socketio.on('message')
def handle_message(data):
    room = data['room']
    message = data['message']
    # Send a message to the specified room
    send(message, to=room)
