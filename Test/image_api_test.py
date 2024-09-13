import json
import unittest
import requests


# Configuration for the tests
PORT = 5000  
IP = "10.0.0.6"
FAST_REPLY_TIME_SEC = 10

class ImageUploadAPITest(unittest.TestCase):
    """
    Test suite for the Image Upload API.
    This suite tests various endpoints of an image upload service including login, upload, and user management.
    """
    def setUp(self):
        """
        Set up test variables and URLs.
        This method runs before each test case.
        """
        self.base_url = f"http://{IP}:{PORT}/"
        self.valid_image_file = "uploads/dog.jpg"
        self.invalid_image_file = "uploads/invalid_image.txt"
        self.login_data = {"username": "admin", "password": "admin"}


    def _resp_is_json(self, response):
        """
        Helper method to check if response is JSON.
        :param response: Response object to check.
        """
        self.assertEqual("application/json", response.headers.get("Content-Type",""))


    def test_authorized_upload(self):
        """
        Test uploading an image with valid login credentials.
        """
        login_response = requests.post(self.base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        with open(self.valid_image_file, "rb") as file:
            response = requests.post(self.base_url + "upload_image", files={"image": file}, cookies=login_response.cookies)
        
        self._resp_is_json(response)
        self.assertIn("matches", response.json())
        self.assertEqual(200, response.status_code)
        self.assertLess(response.elapsed.total_seconds(), FAST_REPLY_TIME_SEC)  
        
        matches = response.json()['matches']
        self.assertIsInstance(matches, list)
        for match in matches:
            self.assertIsInstance(match, dict)
            self.assertTrue({'name','score'} == set(match.keys()))

    def test_unauthorized_upload(self):    
        """
        Test uploading an image without logging in.
        """  
        with open(self.valid_image_file, "rb") as file:
            response = requests.post(self.base_url + 'upload_image', files={"file": file})
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
        self.assertLess(response.elapsed.total_seconds(), FAST_REPLY_TIME_SEC)  # Check response time


    def test_invalid_image_upload(self):
        """
        Test uploading an invalid image file with valid login credentials.
        """
        login_response = requests.post(self.base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        with open(self.invalid_image_file, "rb") as file:
            response = requests.post(self.base_url + "upload_image", files={"file": file}, cookies=login_response.cookies)
        
        self._resp_is_json(response)
        self.assertEqual(400, response.status_code)
        self.assertLess(response.elapsed.total_seconds(), FAST_REPLY_TIME_SEC)  # Check response time
        
    def test_get_non_existent_result_wa_login(self):
        """
        Test accessing a result that does not exist.
        """
        response = requests.get(self.base_url + 'result')
        self.assertEqual(404, response.status_code)

        response = requests.get(self.base_url + 'result/481')
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)
    
    def test_get_non_existent_result_login(self):
        """
        Test accessing a result that does not exist.
        """
        login_response = requests.post(self.base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        response = requests.get(self.base_url + 'result', cookies=login_response.cookies)
        self.assertEqual(404, response.status_code)

        response = requests.get(self.base_url + 'result/481', cookies=login_response.cookies)
        self._resp_is_json(response)
        self.assertEqual(404, response.status_code)

    def test_login_correct_info(self):
        """
        Test logging in with correct username and password.
        """
        login_data_correct = {'username': 'admin', 'password': 'admin'}
        response_correct = requests.post(self.base_url + 'login', data=login_data_correct, allow_redirects=False)
        self.assertEqual(302, response_correct.status_code)

    
    def test_login_incorrect_password(self):
        """
        Test logging in with correct username but incorrect password.
        """
        login_data_incorrect_password = {'username': 'admin', 'password': 'wrongpassword'}
        response_incorrect_password = requests.post(self.base_url + 'login', data=login_data_incorrect_password)
        self._resp_is_json(response_incorrect_password)
        self.assertEqual(401, response_incorrect_password.status_code)
    

    def test_login_non_exist_user(self):
        """
        Test logging in with non-existent username.
        """
        login_data_non_existent_user = {'username': 'nonexistent', 'password': 'admin'}
        response_non_existent_user = requests.post(self.base_url + 'login', data=login_data_non_existent_user)
        self._resp_is_json(response_non_existent_user)
        self.assertEqual(401, response_non_existent_user.status_code)
    

    def test_logout_witout_be_login(self):
        """
        Test logging out without being logged in.
        """
        logout_response = requests.get(self.base_url + "logout")
        self._resp_is_json(logout_response)
        self.assertEqual(401, logout_response.status_code)

    
    def test_logout(self):
        """
        Test logging out after a successful login.
        """
        login_response = requests.post(self.base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        logout_response = requests.get(self.base_url + "logout", cookies=login_response.cookies, allow_redirects=False)
        self.assertEqual(302, logout_response.status_code)
    

    def test_access_upload_page_without_login(self):
        """
        Test accessing the upload page without logging in.
        """
        response = requests.get(self.base_url + 'upload_image')
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)


    def test_empty_login_fields(self):
        """
        Test logging in with empty username and password fields.
        """
        empty_data = {'username': '', 'password': ''}
        response = requests.post(self.base_url + 'login', data=empty_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)


    def test_signup_existing_username(self):
        """
        Test signing up with a username that already exists.
        """
        existing_user_data = {
            'username': 'admin',
            'firstName': 'Admin',
            'password1': 'password',
            'password2': 'password'
        }
        response = requests.post(self.base_url + 'sign-up', data=existing_user_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)

    def test_signup_unmatched_passwords(self):
        """
        Test signing up with unmatched passwords.
        """
        existing_user_data = {
            'username': 'new_user',
            'firstName': 'new_user',
            'password1': 'password1',
            'password2': 'password2'
        }
        response = requests.post(self.base_url + 'sign-up', data=existing_user_data)
        self._resp_is_json(response)
        self.assertEqual(401, response.status_code)

    
    def test_to_signin_twice(self):
        """
        Test logging in twice with the same credentials.
        """
        login_response = requests.post(self.base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        login_response = requests.post(self.base_url + "login", cookies=login_response.cookies, data=self.login_data)
        self._resp_is_json(login_response)
        self.assertEqual(401, login_response.status_code)
    

    def test_status(self):
        """
        Test the status page format
        """
        response = requests.get(self.base_url + "status")
        self._resp_is_json(response)
        self.assertEqual(200, response.status_code)
        self.assertIn("status", response.json())
        
        status_dict = response.json()['status']
        self.assertIsInstance(status_dict, dict)

        self.assertIn("api_version", status_dict)
        self.assertIn("health", status_dict)
        self.assertIn("processed", status_dict)
        self.assertIn("uptime", status_dict)
        self.assertIn("fail", status_dict['processed'])
        self.assertIn("queued", status_dict['processed'])
        self.assertIn("running", status_dict['processed'])
        self.assertIn("success", status_dict['processed'])

        self.assertIsInstance(status_dict['api_version'], (float, int))
        self.assertIsInstance(status_dict['health'], str)
        self.assertIsInstance(status_dict['processed'], dict)
        self.assertIsInstance(status_dict['uptime'], float)
        self.assertIsInstance(status_dict['processed']['fail'], int)
        self.assertIsInstance(status_dict['processed']['queued'], int)
        self.assertIsInstance(status_dict['processed']['running'], int)
        self.assertIsInstance(status_dict['processed']['success'], int)

    
if __name__ == "__main__":
    with open('TestResults.txt', 'w') as f:
        runner = unittest.TextTestRunner(f, verbosity=2)
        unittest.main(testRunner=runner)
