import os 
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import *
from flask import Blueprint, request

model = get_LLM_model()

# Define Blueprint for views
story_api = Blueprint('story_api', __name__)

@story_api.route("/get_story", methods=['POST'])
def get_response():
    story_details = request.json.get("story_details", {})

    moral_of_the_story = story_details.get("moral_of_the_story", "")
    mode = story_details.get("mode", "")
    main_character_name = story_details.get("main_character_name", "")
    secondary_character_name = story_details.get("secondary_character_name", "")
    similar_story = story_details.get("story_inspiration", "Ignored")

    if not all([moral_of_the_story, mode, main_character_name, secondary_character_name, similar_story]):
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
