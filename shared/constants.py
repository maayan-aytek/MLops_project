import json
import pandas as pd
from pymongo import MongoClient


MONGO_CLIENT = MongoClient('mongodb://10.0.0.7:27017/')

BOOKS_DF = pd.read_csv('./shared/books_data.csv')

QUESTIONS = [
    ("Moral of the story",[]),
    ("Main charcter name",[]),
    ("Secondery charcter name",[]),
    ("Story mode",["Classic", "Creative", "Innovative"]),
    ("Story inspiration",['Ignored'] + list(BOOKS_DF['Name'].drop_duplicates().sort_values()))
]

PARTICIPANTS_LOC = {1:'top',
                    2:'left', 
                    3:'right', 
                    4:'bottom-left', 
                    5:'bottom-right'}

with open('./shared/config.json', 'r') as file:
    config = json.load(file)
    API_KEY = config['API_KEY']
    IP = config['IP']
    LOCAL_IP = config['LOCAL_IP']
    PUBLIC_IP = config['PUBLIC_IP']
    IMAGE_API_PORT = config['IMAGE_API_PORT']
    STORY_API_PORT = config['STORY_API_PORT']
    WEB_SERVER_PORT = config['WEB_SERVER_PORT']
    TEST_PREFIX_UPLOADS_PATH = config['TEST_PREFIX_UPLOADS_PATH']
    IMAGE_API_BASE_URL = f"http://image_rest_api:{IMAGE_API_PORT}/"
    STORY_API_BASE_URL = f"http://story_api:{STORY_API_PORT}/"
    WEB_SERVER_URL = f"http://{PUBLIC_IP}:{WEB_SERVER_PORT}/"