import os
import sys
import unittest
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import PUBLIC_IP, WEB_SERVER_PORT, TEST_PREFIX_UPLOADS_PATH


class AuthTest(unittest.TestCase):
    """
    Test suite for the Image Upload API.
    This suite tests various endpoints of an image upload service including login, upload, and user management.
    """
    
    def setUp(self):
        """
        Set up test variables and URLs.
        This method runs before each test case.
        """
        self.base_url = f'http://{PUBLIC_IP}:{WEB_SERVER_PORT}/'
        self.valid_image_file = f"{TEST_PREFIX_UPLOADS_PATH}/dog.jpg"
        self.invalid_image_file = f"{TEST_PREFIX_UPLOADS_PATH}/invalid_image.txt"
        self.login_data = {"username": "admin", "password": "Aa123"}
        self.signup_data = {
            'username': 'new_user',
            'name': 'new_user',
            'password1': 'Password1!',
            'password2': 'Password1!',
            'gender': 'male',
            'age': 7,
            'interests': ['football', 'coding']
        }


    def _resp_is_json(self, response):
        """
        Helper method to check if response is JSON.
        :param response: Response object to check.
        """
        self.assertEqual("application/json", response.headers.get("Content-Type", ""))
    

    def _login(self):
        """
        Helper method to log in a user and return the response.
        """
        return requests.post(self.base_url + 'login', data=self.login_data, allow_redirects=False)


    def test_get_non_existent_result_without_login(self):
        """
        Test accessing a result that does not exist without being logged in.
        """
        response = requests.post(self.base_url + 'result')
        self.assertEqual(404, response.status_code)

        response = requests.post(self.base_url + 'result/481')
        self._resp_is_json(response)
        self.assertEqual(400, response.status_code)
        self.assertIn('error', response.json())


    def test_get_non_existent_result_login(self):
        """
        Test accessing a result that does not exist with login.
        """
        login_response = self._login()
        self.assertEqual(302, login_response.status_code)

        response = requests.post(self.base_url + 'result', cookies=login_response.cookies)
        self.assertEqual(404, response.status_code)

        response = requests.post(self.base_url + 'result/481', cookies=login_response.cookies)
        self._resp_is_json(response)
        self.assertEqual(404, response.status_code)


    def test_login_correct_info(self):
        """
        Test logging in with correct username and password.
        """
        response_correct = self._login()
        self.assertEqual(302, response_correct.status_code)


    def test_login_incorrect_password(self):
        """
        Test logging in with correct username but incorrect password.
        """
        login_data_incorrect_password = {'username': 'admin', 'password': 'wrongpassword'}
        response_incorrect_password = requests.post(self.base_url + 'login', data=login_data_incorrect_password)
        self._resp_is_json(response_incorrect_password)
        self.assertEqual(401, response_incorrect_password.status_code)
        self.assertIn('Incorrect username or password.', response_incorrect_password.json()['error']['message'])


    def test_login_non_exist_user(self):
        """
        Test logging in with non-existent username.
        """
        login_data_non_existent_user = {'username': 'nonexistent', 'password': 'Aa123'}
        response_non_existent_user = requests.post(self.base_url + 'login', data=login_data_non_existent_user)
        self._resp_is_json(response_non_existent_user)
        self.assertEqual(401, response_non_existent_user.status_code)
        self.assertIn('Incorrect username or password.', response_non_existent_user.json()['error']['message'])


    def test_logout_without_being_logged_in(self):
        """
        Test logging out without being logged in.
        """
        logout_response = requests.get(self.base_url + "logout")
        self._resp_is_json(logout_response)
        self.assertEqual(400, logout_response.status_code)
        self.assertIn('You are unauthorized access this page, please log in.', logout_response.json()['error']['message'])


    def test_logout(self):
        """
        Test logging out after a successful login.
        """
        login_response = self._login()
        self.assertEqual(302, login_response.status_code)

        logout_response = requests.get(self.base_url + "logout", cookies=login_response.cookies, allow_redirects=False)
        self.assertEqual(200, logout_response.status_code)


    def test_access_upload_page_without_login(self):
        """
        Test accessing the upload page without logging in.
        """
        for method in ['sync', 'async']:
            with open(self.valid_image_file, "rb") as file:
                response = requests.post(self.base_url + "classify_image",
                                                files={"image": file},
                                                data={'method': method})
                
            self._resp_is_json(response)
            self.assertEqual(400, response.status_code)
            self.assertIn('You are unauthorized access this page, please log in.', response.json()['error']['message'])


    def test_empty_login_fields(self):
        """
        Test logging in with empty username and password fields.
        """
        empty_data = {'username': '', 'password': ''}
        response = requests.post(self.base_url + 'login', data=empty_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
        self.assertIn('Incorrect username or password.', response.json()['error']['message'])


    def test_signup_existing_username(self):
        """
        Test signing up with a username that already exists.
        """
        existing_user_data = {
            'username': 'admin',
            'name': 'admin',
            'password1': 'Aa123',
            'password2': 'Aa123',
            'gender': 'male',
            'age': 7,
            'interests': 'football'
        }
        response = requests.post(self.base_url + 'sign-up', data=existing_user_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
        self.assertIn('Username already exists.', response.json()['error']['message'])

    def test_signup_unmatched_passwords(self):
        """
        Test signing up with unmatched passwords.
        """
        signup_data_unmatched_passwords = {
            'username': 'new_user2',
            'name': 'new_user2',
            'password1': 'Password1!',
            'password2': 'Password2!',
            'gender': 'male',
            'age': 25,
            'interests': 'football, coding'
        }
        response = requests.post(self.base_url + 'sign-up', data=signup_data_unmatched_passwords)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
        self.assertIn('Passwords don\'t match.', response.json()['error']['message'])


    def test_signup_weak_password(self):
        """
        Test signing up with a weak password.
        """
        weak_password_data = self.signup_data.copy()
        weak_password_data['username'] = 'weak_password'
        weak_password_data['password1'] = 'password'
        weak_password_data['password2'] = 'password'
        response = requests.post(self.base_url + 'sign-up', data=weak_password_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
        self.assertIn('Password should contain at least one Upper case letters: A-Z, one Lowercase letters: a-z, and one Number: 0-9.', response.json()['error']['message'])


    def test_successful_signup_and_login(self):
        """
        Test signing up with valid data and then logging in.
        """
        response_signup = requests.post(self.base_url + 'sign-up', data=self.signup_data, allow_redirects=False)
        self.assertEqual(302, response_signup.status_code)  

        login_response = requests.post(self.base_url + 'login', data={'username': self.signup_data['username'], 'password': self.signup_data['password1']}, cookies=response_signup.cookies)
        self.assertEqual(401, login_response.status_code)


    def test_to_signin_twice(self):
        """
        Test logging in twice with the same credentials.
        """
        login_response = self._login()
        self.assertEqual(302, login_response.status_code)

        login_response = requests.post(self.base_url + 'login', data={'username': self.signup_data['username'], 'password': self.signup_data['password1']}, cookies=login_response.cookies)
        self._resp_is_json(login_response)
        self.assertEqual(401, login_response.status_code)
        self.assertIn('The user already login.', login_response.json()['error']['message'])


if __name__ == "__main__":
    unittest.main()
