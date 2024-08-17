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

QUESTIONS = [
    ("Moral of the story",[]),
    ("Main charcter name",[]),
    ("Secondery charcter name",[]),
    ("Story mode",["Classic", "Creative", "Innovative"]),
    ("Story inspiration",["Ignored", "Where the Wild Things Are", "The Very Hungry Caterpillar", "Charlotte's Web", "Harry Potter and the Sorcerer's Stone", "Goodnight Moon"])
]

participent_loc_dict={1:'top',2:'left', 3:'right', 4:'bottom-left', 5:'bottom-right'}

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']
    IP = secrets['IP']
    IP = '127.0.0.1'
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
                "answers": {},
                "sid_list": [],
                "usernames":[current_user.username],
                "position": {name:participent_loc_dict[1]}
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
            rooms[code]['usernames'].append(current_user.username)
            rooms[code]['position'][name] = participent_loc_dict[rooms[code]['num_members']]
            session["room"] = code
            session["name"] = name

            return redirect(url_for("views.lobby"))
    
    return render_template("handle_room_request.html")


@views.route("/lobby")
def lobby():
    rooms = current_app.config['rooms']
    room = session.get("room")

    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("views.handle_room_request"))

    return render_template("lobby.html", code=room, participants=rooms[room]["participants"], is_full=rooms[room]["num_members"] >= rooms[room]["max_participants"])

@socketio.on("connect_lobby")
def connect_lobby():
    rooms = current_app.config['rooms']
    room = session.get("room")

    if not room or room not in current_app.config['rooms']:
        return
    
    participants = current_app.config['rooms'][room]['participants']
    is_full = current_app.config['rooms'][room]['num_members'] >= current_app.config['rooms'][room]['max_participants']
    
    # add sids
    if request.sid not in rooms[room]['sid_list']:
        rooms[room]['sid_list'].append(request.sid)

    # Emit updated participants list and full status to the room
    emit('update_participants', {'participants': participants, 'is_full': is_full}, room=rooms[room]['sid_list'])


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
        rooms[room_code]['sid_list'].append(request.sid)
        emit("finish_turn", {"room_code":room_code}, room=request.sid)


@socketio.on("message")
def handle_message(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    if room_code and room_code in rooms:
        rooms[room_code]["messages"].append(data)

        emit("message", data, room=rooms[room_code]['sid_list'])


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
            rooms[room_code]["answers"][(name, question)] = answer

            # update next turn
            rooms[room_code]['turn_number'] += 1
            

            is_last_turn = current_turn+1==len(QUESTIONS)

            # if not is_last_turn:
            emit("update_participant_data", {"current_participant_name": current_participant,
                                                "current_turn":current_turn,
                                                "question":question,
                                                "answer":answer}, room=rooms[room_code]['sid_list'])
            
            emit("finish_turn", {"room_code": room_code,
                                 "is_last_turn": is_last_turn}, room=rooms[room_code]['sid_list'])
        else:
            emit("unauthorized", {"message": "It's not your turn to answer."}, room=rooms[room_code]['sid_list'])

@socketio.on("generate_story")
def generate_story(room_code=None):
    rooms = current_app.config['rooms']
    room_code = room_code.get("room_code")
    name = session.get('name')

    current_turn = rooms[room_code]['turn_number']
    participants_order = rooms[room_code]["participants_order"]
    n_members = rooms[room_code]["num_members"]
    current_participant = participants_order[current_turn % n_members]

    if current_participant == name:
        answers = list(rooms[room_code]['answers'].values())
        story_details = {
                            "members":rooms[room_code]['usernames'],
                            "moral_of_the_story": answers[0],
                            "mode":answers[1],
                            "main_character_name":answers[2],
                            "secondary_character_name":answers[3],
                            "story_inspiration":answers[4]
                        }
                        
        response = requests.post(API_BASE_URL + "get_story", json={"story_details": story_details})
        story_dict = response.json()

        print(story_dict)
        socketio.emit("story", {"title":story_dict["title"],
                                "story": story_dict["story"]}, room=rooms[room_code]['sid_list'])

@socketio.on("next_turn")
def next_turn(room_code=None):
    rooms = current_app.config['rooms']
    room_code = room_code.get("room_code")
    name = session.get('name')

    if not room_code:
        room_code = session.get("room")
    
    if room_code and room_code in rooms:
        current_turn = rooms[room_code]['turn_number']
        participants_order = rooms[room_code]["participants_order"]
        n_members = rooms[room_code]["num_members"]
        current_participant = participants_order[current_turn % n_members]

        if current_turn<len(QUESTIONS):
            current_question, options = QUESTIONS[current_turn]

            emit("question", {
                "question": current_question,
                "options":options,
                "is_participant_turn": current_participant == name,
                "current_participant_name": current_participant,
            }, room=request.sid)


@socketio.on("connect_room")
def connect_room():
    rooms = current_app.config['rooms']
    room = session.get("room")
    name = session.get('name')

    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    emit("redirect_to_room", {"url": url_for("views.room")}, room=request.sid)


@socketio.on("connect")
def connect():
    # print("disconnect", session.get("name"))
    # name = session.get('name')
    pass
    # rooms = current_app.config['rooms']
    # room = session.get("room")
    # name = session.get('name')

    # if not room or not name:
    #     return
    # if room not in rooms:
    #     leave_room(room)
    #     return

    # join_room(room)
    # # send({"name": name, "message": "has entered the room"}, room=room)
    # print(f"{name} joined room {room}")
    # return redirect(url_for("views.room"))

@socketio.on("disconnect")
def disconnect():
    # print("disconnect", session.get("name"))
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
