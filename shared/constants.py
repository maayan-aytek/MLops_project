import json


QUESTIONS = [
    ("Moral of the story",[]),
    ("Main charcter name",[]),
    ("Secondery charcter name",[]),
    ("Story mode",["Classic", "Creative", "Innovative"]),
    ("Story inspiration",["Ignored", "Where the Wild Things Are", "The Very Hungry Caterpillar", "Charlotte's Web", "Harry Potter and the Sorcerer's Stone", "Goodnight Moon"])
]

PARTICIPANTS_LOC = {1:'top',
                    2:'left', 
                    3:'right', 
                    4:'bottom-left', 
                    5:'bottom-right'}

with open('./shared/secrets.json', 'r') as file:
    secrets = json.load(file)
    API_KEY = secrets['API_KEY']
    IP = secrets['IP']
    # IP = '127.0.0.1'
    IMAGE_API_PORT = secrets['IMAGE_API_PORT']
    STORY_API_PORT = secrets['STORY_API_PORT']
    IMAGE_API_BASE_URL = f"http://{IP}:{IMAGE_API_PORT}/"
    STORY_API_BASE_URL = f"http://{IP}:{STORY_API_PORT}/"