import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import json
import time
import random
import base64
import requests
import PIL.Image
from typing import Union
from shared.utils import *
from .app import socketio
from string import ascii_uppercase
import google.generativeai as genai
from flask_login import login_required, current_user
from flask_socketio import emit, join_room, leave_room, send
from flask import Blueprint, render_template, request, redirect, url_for, Response, current_app, session

API_PORT = 8000  
API_IP = "192.168.1.21"
API_BASE_URL = f"http://{API_IP}:{API_PORT}/"

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']
    IP = secrets['IP']
    API_PORT = secrets['API_PORT']
    API_BASE_URL = f"http://{IP}:{API_PORT}/"

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


def generate_unique_code(length, rooms):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code

@views.route('/handle_room_request', methods=["POST", "GET"])
def handle_room_request():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        num_participants = request.form.get("participants")
        action = request.form.get("action")  # Use the action parameter to determine the form submission
        rooms = current_app.config['rooms']

        if not name:
            return render_template("handle_room_request.html", error="Please enter a name.", name=name)
        
        if action == "create":
            if not num_participants:
                return render_template("handle_room_request.html", error="Please select the number of participants.", name=name)

            # Create a new room with a unique code
            room = generate_unique_code(4, rooms)
            rooms[room] = {"members": 1, "max_participants": int(num_participants), "messages": []}
            print("1", rooms[room])
            session["room"] = room
            session["name"] = name
            session["participants"] = num_participants
        
            return redirect(url_for("views.room"))
        
        elif action == "join":
            code = request.form.get("code")
            if not code:
                return render_template("handle_room_request.html", error="Please enter a room code.", name=name)
            if code not in rooms:
                return render_template("handle_room_request.html", error="Room does not exist.", name=name, code=code)
            
            rooms[code]['members'] += 1
            if rooms[code]['members'] > rooms[code]['max_participants']:
                return render_template("handle_room_request.html", error="The room is already full, please create a new room.", name=name, code=code)
            
            session["room"] = code
            session["name"] = name
        
            return redirect(url_for("views.room"))
    
    return render_template("handle_room_request.html")



@views.route("/room")
def room():
    rooms = current_app.config['rooms']
    room = session.get("room")

    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("views.handle_room_request"))

    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("message")
def message(data):
    rooms = current_app.config['rooms']
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    rooms = current_app.config['rooms']
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    rooms = current_app.config['rooms']
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")
