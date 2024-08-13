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

questions = [
    "Moral of the story",
    "Main charcter name",
    "Secondery charcter name",
    "Story mode",
    "Story inspiration"
]

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
        return redirect(url_for('views.choose_action'))
    return redirect(url_for('views.home_view'))

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


@views.route('/home', methods=['GET'])
def home_view():
    return render_template('base.html', user=current_user)

@views.route('/about_us', methods=['GET'])
def about_us():
    return render_template('about_us.html', user=current_user)

@views.route('/choose_action', methods=['GET'])
def choose_action():
    return render_template('choose_action.html', user=current_user)

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
            rooms[room] = {
                "num_members": 1,
                "turn_number": 0,
                "max_participants": int(num_participants),
                "messages": [],
                "participants": [name],
                "answers": {}
            }
            session["room"] = room
            session["name"] = name
        
            return redirect(url_for("views.lobby"))
        
        elif action == "join":
            code = request.form.get("code")
            if not code:
                return render_template("handle_room_request.html", error="Please enter a room code.", name=name)
            if code not in rooms:
                return render_template("handle_room_request.html", error="Room does not exist.", name=name, code=code)
            
            if rooms[code]['num_members'] >= rooms[code]['max_participants']:
                return render_template("handle_room_request.html", error="The room is already full, please create a new room.", name=name, code=code)
            
            rooms[code]['num_members'] += 1
            rooms[code]['participants'].append(name)
            session["room"] = code
            session["name"] = name
        
            return redirect(url_for("views.lobby"))
    
    return render_template("handle_room_request.html")


@views.route("/lobby")
def lobby():
    rooms = current_app.config['rooms']
    room = session.get("room")
    print(rooms)
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("views.handle_room_request"))

    return render_template("lobby.html", code=room, participants=rooms[room]["participants"], is_full=rooms[room]["num_members"] >= rooms[room]["max_participants"])

@socketio.on("connect_lobby")
def connect_lobby():
    room = session.get("room")
    name = session.get("name")
    if not room or room not in current_app.config['rooms']:
        return
    
    participants = current_app.config['rooms'][room]['participants']
    is_full = current_app.config['rooms'][room]['num_members'] >= current_app.config['rooms'][room]['max_participants']
    
    # Emit updated participants list and full status to the room
    emit('update_participants', {'participants': participants, 'is_full': is_full}, room=room)
    print(f"{name} joined room {room} lobby")
    
    # Notify other participants about the new member
    send({"name": name, "message": "has joined the room"}, to=room)


@views.route("/room")
def room():
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    if room_code is None or room_code not in rooms:
        return redirect(url_for("handle_room_request"))

    # define participants order done
    if "participants_order" not in rooms[room_code]:
        rooms[room_code]["participants_order"] = random.sample(rooms[room_code]["participants"], len(rooms[room_code]["participants"]))

    return render_template("room.html", code=room_code, messages=rooms[room_code]["messages"])


@socketio.on("join")
def handle_join(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if room_code and room_code in rooms:
        emit("finish_turn", {"room_code":room_code}, room=room_code)


@socketio.on("message")
def handle_message(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    if room_code and room_code in rooms:
        rooms[room_code]["messages"].append(data)

        emit("message", data, room=room_code)


@socketio.on("answer")
def handle_answer(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    name = session.get('name')
    
    if room_code and room_code in rooms:
        current_turn = rooms[room_code]["turn_number"]
        participants_order = rooms[room_code]["participants_order"]
        n_members = rooms[room_code]["num_members"]
        
        current_participant = participants_order[current_turn % n_members]

        if name == current_participant:
            question = data["question"]
            answer = data["answer"]
            rooms[room_code]["answers"][question] = answer

            # update next turn
            rooms[room_code]['turn_number'] += 1
            emit("finish_turn", {"room_code":room_code}, room=room_code)
        else:
            emit("unauthorized", {"message": "It's not your turn to answer."}, room=room_code)



@socketio.on("next_turn")
def handle_next_turn(room_code=None):
    rooms = current_app.config['rooms']
    room_code = room_code.get("room_code")
    name = session.get('name')
    print("room_code", room_code)
    if not room_code:
        room_code = session.get("room")
    
    if room_code and room_code in rooms:

        current_turn = rooms[room_code]['turn_number']
        participants_order = rooms[room_code]["participants_order"]
        n_members = rooms[room_code]["num_members"]
        
        if current_turn<len(questions):
            current_question = questions[current_turn]
            current_participant = participants_order[current_turn % n_members]

        print(current_participant, name, current_turn, current_participant==name)
        emit("question", {
            "question": current_question,
            "is_participant_turn": current_participant == name
        }, room=request.sid)


@socketio.on("connect")
def connect(auth):
    rooms = current_app.config['rooms']
    room = session.get("room")
    name = session.get('name')

    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    print(f"{name} joined room {room}")
    return redirect(url_for("views.room"))

@socketio.on("disconnect")
def disconnect():
    pass
    # rooms = current_app.config['rooms']
    # room = session.get("room")
    # name = session.get("name")
    # leave_room(room)

    # if room in rooms:
    #     rooms[room]["num_members"] -= 1
    #     if rooms[room]["num_members"] <= 0:
    #         del rooms[room]
    
    # send({"name": name, "message": "has left the room"}, to=room)
    # print(f"{name} has left the room {room}")
