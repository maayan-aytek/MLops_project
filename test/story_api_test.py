import time
import os
import sys
import requests
import unittest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import LOCAL_IP, STORY_API_PORT


class StoryAPITest(unittest.TestCase):
    def setUp(self):
        self.base_url = f'http://{LOCAL_IP}:{STORY_API_PORT}/'
        self.valid_story_details = {
            'ages': [4, 5, 6],
            'interests': ['football', 'paint', 'princess'],
            'genders': ['male', 'male', 'female'],
            'moral_of_the_story': 'Be kind',
            'mode': 'creative',
            'main_character_name': 'Ori',
            'secondary_character_name': 'Maayan',
            'story_inspiration': 'Ignored'
        }
        self.invalid_story_details = {
            'ages': [4, 5, 6],
            'genders': ['male', 'male', 'female'],
            'moral_of_the_story': 'Be kind',
            'mode': 'creative',
            'main_character_name': 'Ori',
            'secondary_character_name': 'Maayan',
            'story_inspiration': ''  # Missing required field
        }


    def test_valid_story_generation(self):
        response = requests.post(self.base_url + 'get_story', json={"story_details": self.valid_story_details})
        self.assertEqual(200, response.status_code)
        response_data = response.json()
        self.assertIn("title", response_data)
        self.assertIn("story", response_data)
        self.assertIsInstance(response_data['title'], str)
        self.assertIsInstance(response_data['story'], str)


    def test_invalid_story_details(self):
        response = requests.post(self.base_url + 'get_story', json={"story_details": self.invalid_story_details})
        self.assertEqual(401, response.status_code)
        response_data = response.json()
        self.assertEqual(response_data['error']['code'], 401)


    def test_missing_fields(self):
        missing_fields_cases = [
            {'moral_of_the_story': '', 'story_inspiration': 'Ignored'},
            {'ages': [], 'story_inspiration': 'Ignored'},
            {'main_character_name': '', 'secondary_character_name': '', 'story_inspiration': 'Ignored'},
        ]
        for case in missing_fields_cases:
            story_details = {**self.valid_story_details, **case}
            response = requests.post(self.base_url + 'get_story', json={"story_details": story_details})
            self.assertEqual(401, response.status_code)
            


if __name__ == "__main__":
    unittest.main()
