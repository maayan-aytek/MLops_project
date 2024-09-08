import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import random
import requests
from .app import socketio
from shared.utils import *
from shared.constants import * 
from flask_login import current_user, login_required
from flask_socketio import emit, join_room, leave_room
from flask import Blueprint, render_template, request, redirect, url_for, current_app, session

story_generation = Blueprint('story_generation', __name__)


@login_required
@story_generation.route('/handle_room_request', methods=["POST", "GET"])
def handle_room_request():
    session.clear()
    if request.method == "POST":
        nickname = request.form.get("nickname")
        num_participants = request.form.get("participants")
        action = request.form.get("action")  # Use the action parameter to determine the form submission
        rooms = current_app.config['rooms']

        if not nickname:
            return render_template("handle_room_request.html", error="Please enter a name.", nick_name=nickname)
        
        if action == "create":
            if not num_participants:
                return render_template("handle_room_request.html", error="Please select the number of participants.", nick_name=nickname)

            # Create a new room with a unique code
            room = generate_unique_code(4, rooms)
            rooms[room] = {
                "turn_number": 0,
                "max_participants": int(num_participants),
                "history": [],
                "sid_list": [],
                "nickname_dict": {current_user.username: nickname}
            }
            session["room"] = room
            
            return redirect(url_for("story_generation.lobby"))
        
        elif action == "join":
            room_code = request.form.get("code")
            if not room_code:
                return render_template("handle_room_request.html", error="Please enter a room code.", nick_name=nickname)
            if room_code not in rooms:
                return render_template("handle_room_request.html", error="Room does not exist.", nick_name=nickname, code=room_code)
            
            n_members = len(rooms[room_code]['nickname_dict'])
            if  n_members >= rooms[room_code]['max_participants']:
                return render_template("handle_room_request.html", error="The room is already full, please create a new room.", nickname=nickname, code=room_code)
            
            rooms[room_code]['nickname_dict'][current_user.username] = nickname
            session["room"] = room_code

            return redirect(url_for("story_generation.lobby"))
    
    return render_template("handle_room_request.html")


@socketio.on("disconnect_room")
def disconnect_room():
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    
    turn_number = rooms[room_code]['turn_number']
    n_members = len(rooms[room_code]['nickname_dict'])
    current_username_turn = rooms[room_code]["participants_order"][turn_number % n_members]
    current_nickname = rooms[room_code]["nickname_dict"][current_user.username]

    rooms[room_code]["participants_order"].remove(current_user.username)
    rooms[room_code]['sid_list'].remove(request.sid)
    del rooms[room_code]["nickname_dict"][current_user.username]

    if n_members - 1 == 0:
        return
        
    print("current_username_turn:", current_username_turn, "current_user.username:",current_user.username)
    emit("AlertleaveRoom", {'nickname': current_nickname, 
                            'call_next_turn':current_username_turn == current_user.username,
                            'room_code':room_code}, room=rooms[room_code]['sid_list'])


@socketio.on("connect_lobby")
def connect_lobby():
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if not room_code or room_code not in rooms:
        return
    
    participants_names = list(rooms[room_code]["nickname_dict"].values())
    is_full = len(participants_names) >= rooms[room_code]['max_participants']
    
    # add sids
    if request.sid not in rooms[room_code]['sid_list']:
        rooms[room_code]['sid_list'].append(request.sid)

    # Emit updated participants list and full status to the room
    emit('update_participants', {'participants': participants_names, 'is_full': is_full}, room=rooms[room_code]['sid_list'])


@login_required
@story_generation.route("/lobby")
def lobby():
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if room_code is None or rooms[room_code]['nickname_dict'][current_user.username] == '' or room_code not in rooms:
        return redirect(url_for("story_generation.handle_room_request"))

    participants_names = list(rooms[room_code]["nickname_dict"].values())
    return render_template("lobby.html", code=room_code, participants=participants_names, is_full=len(participants_names) >= rooms[room_code]["max_participants"])


@socketio.on("connect_room")
def connect_room():
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if not room_code or not rooms[room_code]['nickname_dict'][current_user.username]:
        return
    if room_code not in rooms:
        leave_room(room_code)
        return

    join_room(room_code)
    emit("redirect_to_room", {"url": url_for("story_generation.room")}, room=request.sid)


@login_required   
@story_generation.route("/room")
def room():
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    participants = list(rooms[room_code]['nickname_dict'].keys())

    if room_code is None or room_code not in rooms:
        return redirect(url_for("handle_room_request"))

    # define participants order done
    if "participants_order" not in rooms[room_code]:
        rooms[room_code]["participants_order"] = random.sample(participants, len(participants))

    return render_template("room.html", code=room_code)


@socketio.on("join")
def handle_join(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")
    
    if room_code and room_code in rooms:
        rooms[room_code]['sid_list'].append(request.sid)
        emit("finish_turn", {"room_code":room_code}, room=request.sid)
        emit("update_participant_data", rooms[room_code]["history"], room=rooms[room_code]['sid_list'])


@socketio.on("answer")
def handle_answer(data):
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if room_code and room_code in rooms:
        current_turn = rooms[room_code]["turn_number"]
        participants_order = rooms[room_code]["participants_order"]
        n_members = len(rooms[room_code]['nickname_dict'])
        
        current_participant = participants_order[current_turn % n_members]

        if current_user.username == current_participant:
            question = data["question"]
            answer = data["answer"]
            nickname = rooms[room_code]['nickname_dict'][current_user.username]
            round_details =  {"current_participant_name": nickname,
                              "current_turn":current_turn,
                              "question":question,
                              "answer":answer}
            rooms[room_code]["history"].append(round_details)
                
            # update next turn
            rooms[room_code]['turn_number'] += 1
            is_last_turn = current_turn + 1 == len(QUESTIONS)

            emit("update_participant_data", rooms[room_code]["history"], room=rooms[room_code]['sid_list'])
            
            emit("finish_turn", {"room_code": room_code,
                                 "is_last_turn": is_last_turn}, room=rooms[room_code]['sid_list'])
        else:
            emit("unauthorized", {"message": "It's not your turn to answer."}, room=rooms[room_code]['sid_list'])


@socketio.on("next_turn")
def next_turn(room_code=None):
    rooms = current_app.config['rooms']
    room_code = room_code.get("room_code")

    if not room_code:
        room_code = session.get("room")
    
    if room_code and room_code in rooms:
        current_turn = rooms[room_code]['turn_number']
        participants_order = rooms[room_code]["participants_order"]
        n_members = len(rooms[room_code]['nickname_dict'])
        current_participant = participants_order[current_turn % n_members]

        if current_turn < len(QUESTIONS):
            current_question, options = QUESTIONS[current_turn]

            emit("question", {
                 "question": current_question,
                 "options": options,
                 "is_participant_turn": current_participant == current_user.username,
                 "current_participant_name": rooms[room_code]['nickname_dict'][current_participant],
            }, room=request.sid)


@socketio.on("generate_story")
def generate_story(room_code=None):
    rooms = current_app.config['rooms']
    room_code = room_code.get("room_code")

    current_turn = rooms[room_code]['turn_number']
    participants_order = rooms[room_code]["participants_order"]
    n_members = len(rooms[room_code]["nickname_dict"])
    current_participant = participants_order[current_turn % n_members]

    if current_participant == current_user.username:
        db = current_app.config['MONGO_DB']
        ages, interests, genders = [], [], []
        user_names = rooms[room_code]['nickname_dict'].keys()
        for username in user_names:
            user = db.find_one({"username": username})
            ages.append(user['age'])
            interests.extend(user['interests'])
            genders.append(user['gender'])

        answers = [details['answer'] for details in rooms[room_code]['history']]
        story_details = {
                            "ages": ages,
                            "interests": interests,
                            "genders": genders,
                            "moral_of_the_story": answers[0],
                            "mode": answers[1],
                            "main_character_name": answers[2],
                            "secondary_character_name": answers[3],
                            "story_inspiration": answers[4]
                        }
                        
        response = requests.post(STORY_API_BASE_URL + "get_story", json={"story_details": story_details})
        story_dict = response.json()

        socketio.emit("story", {"title": story_dict["title"],
                                "story": story_dict["story"]}, room=rooms[room_code]['sid_list'])


@socketio.on("connect")
def connect():
    pass


@socketio.on("disconnect")
def disconnect():
    pass

