import os 
import json
import sys
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from shared.utils import *
from shared.constants import BOOKS_DF
from flask import Blueprint, request

model = get_LLM_model()

# Define Blueprint for views
story_api = Blueprint('story_api', __name__)

@story_api.route("/get_story", methods=['POST'])
def get_response():
    story_details = request.json.get("story_details", {})
    ages = story_details.get("ages", [])
    interests = story_details.get("interests", [])
    sampled_interest = random.choices(interests, k=1)[0]
    genders = story_details.get("genders", [])
    moral_of_the_story = story_details.get("moral_of_the_story", "")
    mode = story_details.get("mode", "")
    main_character_name = story_details.get("main_character_name", "")
    secondary_character_name = story_details.get("secondary_character_name", "")
    similar_story = story_details.get("story_inspiration", "Ignored")
    similar_story_description = "" if similar_story == "Ignored" else BOOKS_DF[BOOKS_DF['Name'] == similar_story]['Description'].values[0]
    
    if not all([moral_of_the_story, mode, main_character_name, secondary_character_name, similar_story]):
        return create_json_response({'error': {'code': 401, 'message': 'One of the deatils field is miising!'}}, 401)

    story_reading_time = 2

    if similar_story != "Ignored":
        # If story inspiration is given then we will concatenate this part to the prompt
        similar_story_parts = f"The story should be inspired by '{similar_story} children book. Here is the book description: {similar_story_description}.",
                           
    else:
        similar_story_parts = ""

    prompt = f"""You are a creative story writer tasked with crafting engaging children's stories. 
            Create a captivating children's story for a group of {genders} aged {ages} years. The story should be approximately {story_reading_time} minutes long, focusing on the moral: '{moral_of_the_story}'.
            The story mode should be {mode}. The main character will be named '{main_character_name}', with a secondary character named '{secondary_character_name}'.
            The children are interested in {sampled_interest}. Feel free to incorporate this interest, but make sure it is naturally fit within the story's context. 
            {similar_story_parts}
              
              The output should be in JSON format with the following keys:
              - "title": the title of the story
              - "story": the full story
              
              Example format:
              {{
                  "title": <the story title>
                  "story": <The full story>
              }}

              Provide only the JSON output without any additional text or explanation.
              """

    
    response = model.generate_content([prompt], stream=True)
    response.resolve()
    story_dict = json.loads(response.text)
    
    return create_json_response({"title":story_dict['title'],
                                 "story": story_dict['story']}, 200)
