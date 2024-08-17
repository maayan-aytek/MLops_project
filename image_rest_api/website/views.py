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
            return create_json_response({'error':'got an unhandle exception'}, 400)
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


@views.route("/get_story", methods=['POST'])
def get_response():
    story_details = request.json.get("story_details", {})

    moral_of_the_story = story_details.get("moral_of_the_story", "")
    mode = story_details.get("mode", "")
    main_character_name = story_details.get("main_character_name", "")
    secondary_character_name = story_details.get("secondary_character_name", "")
    similar_story = story_details.get("story_inspiration", "Ignored")

    if not all([moral_of_the_story, mode, main_character_name, secondary_character_name, similar_story]):
        print(moral_of_the_story)
        print(mode)
        print(main_character_name)
        print(similar_story)
        print(similar_story_description)
        return create_json_response({'error': {'code': 401, 'message': 'One of the deatils field is miising!'}}, 401)

    child_age = 7
    child_gender = "male"
    child_interests = ["football"]
    story_reading_time = 2
    similar_story_description = ""
    similar_story = "Ignore"

    if similar_story != "Ignored":
        # If story inspiration is given then we will concatenate this part to the prompt
        similar_story_parts = f"The story should be inspired by '{similar_story} children book. Here is the book description: {similar_story_description}.",
                           
    else:
        similar_story_parts = ""

    prompt = f"""Generate children story suitable for a {child_age}-year-old {child_gender} child with interests in {child_interests[0]}. 
                The story should be around {story_reading_time} minutes long. The moral of the story should be '{moral_of_the_story}'.
                The mode of the story should be {mode}. The main character of the story should be named '{main_character_name}'.
                Please note that the story doesn't have to include all interests mentioned; it can choose to include only a subset of them.
                Also, avoid mixing unrelated interests. If there are multiple interests provided, choose at random only one that fits the story context best.
                {similar_story_parts}
                Your output must be in the following format: 
                Title: ...
                Description: ...
                Story: ...
                """
    
    response = model.generate_content([prompt], stream=True)
    response.resolve()

    # Split generated content into story, title, and description
    parts = response.text.split("Title:")
    if 'Story:' in parts[1].split("Description:")[1]:
        split_by = 'Story:'
    elif '<br/>' in parts[1].split("Description:")[1]:
        split_by = '<br/>'
    else:
        split_by = '\n\n'
    title = parts[1].split("Description:")[0].strip().replace('*', '').replace('#','')
    description = parts[1].split("Description:")[1].split(split_by)[0].strip().replace('*', '').replace('#','')
    story = parts[1].split(description)[1].replace('Story:', '').replace('*', '').replace('#','').strip()
    
    return create_json_response({"title":title,
                                 "description":description,
                                 "story": story}, 200)


# @views.route("/get_story", methods=['GET'])
# def get_response(child_age, child_gender, child_interests, story_reading_time, moral_of_the_story, mode, main_character_name, similar_story, similar_story_description):
    
#     # Choosing different interest for each story to increase the variance
#     child_interests = child_interests.split(", ")
#     if len(child_interests) < 3: 
#         child_interests = random.choices(child_interests, k=3)
#     else:
#         child_interests = random.sample(child_interests, k=3)
#     prompts = []
#     if similar_story != "Ignored":
#         # If story inspiration is given then we will concatenate this part to the prompt
#         similar_story_parts = [f"The story should be inspired by '{similar_story} children book. Here is the book description: {similar_story_description}.",
#                             f"{similar_story}' book is the inspiration, it should echo the essence of its plot without direct replication. Here is the book description: {similar_story_description},",
#                             f"{similar_story}' bookk aim to capture the story spirit and integrate it thoughtfully with a unique twist. Here is the book description: {similar_story_description}."]
#     else:
#         similar_story_parts = ["", "", ""]

#     # Build 3 different prompts to increase the variance between stories 
#     prompts.append(f"""Generate children story suitable for a {child_age}-year-old {child_gender} child with interests in {child_interests[0]}. 
#                     The story should be around {story_reading_time} minutes long. The moral of the story should be '{moral_of_the_story}'.
#                     The mode of the story should be {mode}. The main character of the story should be named '{main_character_name}'.
#                     Please note that the story doesn't have to include all interests mentioned; it can choose to include only a subset of them.
#                     Also, avoid mixing unrelated interests. If there are multiple interests provided, choose at random only one that fits the story context best.
#                     {similar_story_parts[0]}
#                     Your output must be in the following format: 
#                     Title: ...
#                     Description: ...
#                     Story: ...
#                     """)
#     prompts.append(f"""Craft a tale for a {child_age}-year-old {child_gender} interested in {child_interests[1]}. 
#                     This narrative should unfold over approximately {story_reading_time} minutes. 
#                     Central to the story is the moral '{moral_of_the_story}', which should be seamlessly woven into the plot. 
#                     The narrative style is to be {mode}, and the protagonist, named '{main_character_name}', should embody the story's essence. 
#                     While the story may draw from the child's interests, it should focus on a primary theme to maintain coherence. 
#                     {similar_story_parts[1]}
#                     Your output must be in the following format: 
#                     Title: ...
#                     Description: ...
#                     Story: ...
#                     """)
#     prompts.append(f"""Create a story appropriate for a {child_age}-year-old {child_gender}, with a spotlight on {child_interests[2]}. 
#                     The duration of the story should be close to {story_reading_time} minutes. 
#                     Importantly, the storyline should impart the lesson '{moral_of_the_story}', and be presented in a {mode} manner.
#                     '{main_character_name}' should lead the narrative as the principal character. While the tale can tap into various interests,
#                     it should primarily revolve around one to ensure a unified theme. 
#                     {similar_story_parts[2]}
#                     Your output must be in the following format: 
#                     Title: ...
#                     Description: ...
#                     Story: ...
#                     """)
#     outputs = []
#     for i in range(3):
#         completion = openAI_client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You're a story generator tasked with creating captivating children's stories tailored to individual preferences."},
#                 {"role": "user", "content": prompts[i]},
#             ],
#         )
#         outputs.append(completion.choices[0])

#     # Extract the stories from the LLM output
#     stories = []
#     for choice in outputs:
#         generated_content = choice.message.content
#         print("-----------")
#         print(generated_content)
#         # Split generated content into story, title, and description
#         parts = generated_content.split("Title:")
#         if 'Story:' in parts[1].split("Description:")[1]:
#             split_by = 'Story:'
#         elif '<br/>' in parts[1].split("Description:")[1]:
#             split_by = '<br/>'
#         else:
#             split_by = '\n\n'
#         title = parts[1].split("Description:")[0].strip().replace('*', '').replace('#','')
#         description = parts[1].split("Description:")[1].split(split_by)[0].strip().replace('*', '').replace('#','')
#         story = parts[1].split(description)[1].replace('Story:', '').replace('*', '').replace('#','').strip()
#         stories.append({'story':story, 'title':title, 'description':description})

#     return stories