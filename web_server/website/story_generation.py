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
    """
    Handles the creation and joining of rooms.
    Clears the session and processes form data for creating or joining a room. Validates inputs and redirects
    to the appropriate room or lobby if successful.

    Returns:
        Response: Redirects to the lobby or room page, or re-renders the form with an error message if the
        input is invalid.
    """
    session.clear()
    if request.method == "POST":
        nickname = request.form.get("nickname")
        num_participants = request.form.get("participants")
        action = request.form.get("action")
        rooms = current_app.config['rooms']

        if not nickname:
            return render_template("handle_room_request.html", error="Please enter a name.", nick_name=nickname)

        if action == "create":
            if not num_participants:
                return render_template("handle_room_request.html", error="Please select the number of participants.",
                                       nick_name=nickname)

            room_code = generate_unique_code(4, rooms)
            rooms[room_code] = {
                "turn_number": 0,
                "max_participants": int(num_participants),
                "history": [],
                "sid_list": [],
                "nickname_dict": {current_user.username: nickname}
            }
            session["room"] = room_code

            return redirect(url_for("story_generation.lobby", room_code=room_code))

        elif action == "join":
            room_code = request.form.get("code")
            if not room_code:
                return render_template("handle_room_request.html", error="Please enter a room code.",
                                       nick_name=nickname)
            if room_code not in rooms:
                return render_template("handle_room_request.html", error="Room does not exist.", nick_name=nickname,
                                       code=room_code)

            n_members = len(rooms[room_code]['nickname_dict'])
            if n_members >= rooms[room_code]['max_participants']:
                return render_template("handle_room_request.html",
                                       error="The room is already full, please create a new room.", nickname=nickname,
                                       code=room_code)

            rooms[room_code]['nickname_dict'][current_user.username] = nickname
            session["room"] = room_code

            return redirect(url_for("story_generation.lobby", room_code=room_code))

    return render_template("handle_room_request.html")


@socketio.on("disconnect_room")
def disconnect_room():
    """
    Handles the event of a user disconnecting from a room.
    Removes the user from the room's participant list and emits an alert to notify other participants.
    """
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

    emit("AlertleaveRoom", {'nickname': current_nickname,
                            'call_next_turn': current_username_turn == current_user.username,
                            'room_code': room_code}, room=rooms[room_code]['sid_list'])


@socketio.on("connect_lobby")
def connect_lobby():
    """
    Handles a user's connection to the lobby.
    Adds the user's session ID to the room and emits an event to update the participant list.
    """
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if not room_code or room_code not in rooms:
        return

    participants_names = list(rooms[room_code]["nickname_dict"].values())
    is_full = len(participants_names) >= rooms[room_code]['max_participants']

    if request.sid not in rooms[room_code]['sid_list']:
        rooms[room_code]['sid_list'].append(request.sid)

    emit('update_participants', {'participants': participants_names, 'is_full': is_full},
         room=rooms[room_code]['sid_list'])


@login_required
@story_generation.route("/lobby/<room_code>")
def lobby(room_code: str):
    """
    Renders the lobby page for a specific room.
    Generates a QR code for the room and displays the list of participants.

    Args:
        room_code (str): The code of the room.

    Returns:
        Response: Renders the lobby page or redirects to the room request page if the room is invalid.
    """
    rooms = current_app.config['rooms']
    qr_code = generate_qr_code(WEB_SERVER_URL + f'room/{room_code}')

    if room_code is None or rooms[room_code]['nickname_dict'][current_user.username] == '' or room_code not in rooms:
        return redirect(url_for("story_generation.handle_room_request"))

    participants_names = list(rooms[room_code]["nickname_dict"].values())
    return render_template("lobby.html", code=room_code, participants=participants_names, qr_code=qr_code,
                           is_full=len(participants_names) >= rooms[room_code]["max_participants"])


@socketio.on("connect_room")
def connect_room():
    """
    Handles a user's connection to a room.
    Joins the user to the room and emits a redirect event to navigate to the room page.
    """
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if not room_code or not rooms[room_code]['nickname_dict'][current_user.username]:
        return
    if room_code not in rooms:
        leave_room(room_code)
        return

    join_room(room_code)
    emit("redirect_to_room", {"url": url_for("story_generation.room", room_code=room_code)}, room=request.sid)


@login_required
@story_generation.route("/room/<room_code>")
def room(room_code: str):
    """
    Renders the room page for a specific room.
    Initializes the participant order if it hasn't been set.

    Args:
        room_code (str): The code of the room.

    Returns:
        Response: Renders the room page or redirects to the room request page if the room is invalid.
    """
    rooms = current_app.config['rooms']
    participants = list(rooms[room_code]['nickname_dict'].keys())

    if room_code is None or room_code not in rooms:
        return redirect(url_for("handle_room_request"))

    if "participants_order" not in rooms[room_code]:
        rooms[room_code]["participants_order"] = random.sample(participants, len(participants))

    return render_template("room.html", code=room_code)


@socketio.on("join")
def handle_join(data):
    """
    Handles a user joining a room.
    Adds the user's session ID to the room and emits events to update participant data.

    Args:
        data (dict): Data sent with the event.
    """
    rooms = current_app.config['rooms']
    room_code = session.get("room")

    if room_code and room_code in rooms:
        rooms[room_code]['sid_list'].append(request.sid)
        emit("finish_turn", {"room_code": room_code}, room=request.sid)
        emit("update_participant_data", rooms[room_code]["history"], room=rooms[room_code]['sid_list'])


@socketio.on("answer")
def handle_answer(data):
    """
    Processes an answer submitted by a participant in the room.
    Validates if it's the participant's turn to answer. If valid, appends the answer to the room's history, updates the turn number,
    and emits events to update participant data and indicate if the turn is completed. If not valid, emits an 'unauthorized' event.

    Args:
        data (dict): Contains 'question' and 'answer' submitted by the participant.
    """
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
            round_details = {
                "current_participant_name": nickname,
                "current_turn": current_turn,
                "question": question,
                "answer": answer
            }
            rooms[room_code]["history"].append(round_details)

            rooms[room_code]['turn_number'] += 1
            is_last_turn = current_turn + 1 == len(QUESTIONS)

            emit("update_participant_data", rooms[room_code]["history"], room=rooms[room_code]['sid_list'])

            emit("finish_turn", {"room_code": room_code, "is_last_turn": is_last_turn},
                 room=rooms[room_code]['sid_list'])
        else:
            emit("unauthorized", {"message": "It's not your turn to answer."}, room=rooms[room_code]['sid_list'])


@socketio.on("next_turn")
def next_turn(room_code: str = None):
    """
    Moves the game to the next turn and emits the next question to the participants.
    Determines the current participant's turn and emits the current question and options to the room.

    Args:
        room_code (dict, optional): Contains 'room_code' to identify the room. If not provided, retrieves it from the session.
    """
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
def generate_story(room_code: str = None):
    """
    Generates a story based on participants' answers and emits the final story to the room.
    Collects data such as ages, interests, and answers to questions, sends them to an external story generation API,
    and emits the generated story to all participants in the room.

    Args:
        room_code (dict, optional): Contains 'room_code' to identify the room. If not provided, retrieves it from the session.
    """
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
            "main_character_name": answers[1],
            "secondary_character_name": answers[2],
            "mode": answers[3],
            "story_inspiration": answers[4]
        }

        response = requests.post(STORY_API_BASE_URL + "get_story", json={"story_details": story_details})
        story_dict = response.json()

        socketio.emit("story", {"title": story_dict["title"], "story": story_dict["story"]},
                      room=rooms[room_code]['sid_list'])


@socketio.on("connect")
def connect():
    pass


@socketio.on("disconnect")
def disconnect():
    pass

