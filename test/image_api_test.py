import json
import unittest
import requests
import time

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
        self.web_server_base_url = f'http://127.0.0.1:8000/'
        self.image_api_base_url = f'http://127.0.0.1:8000/'
        self.valid_image_file = "uploads/dog.jpg"
        self.invalid_image_file = "uploads/invalid_image.txt"
        self.login_data = {"username": "admin", "password": "Aa123"}

    def _resp_is_json(self, response):
        """
        Helper method to check if response is JSON.
        :param response: Response object to check.
        """
        self.assertEqual("application/json", response.headers.get("Content-Type",""))


    def test_sync_authorized_upload(self):
        """
        Test uploading an image with valid login credentials.
        """
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        with open(self.valid_image_file, "rb") as file:
            sync_response = requests.post(self.web_server_base_url + "classify_image",
                                            files={"image": file},
                                            data={'method': 'sync'},
                                            cookies=login_response.cookies)
        
        self._resp_is_json(sync_response)
        self.assertIn("matches", sync_response.json())
        self.assertEqual(200, sync_response.status_code)
        
        matches = sync_response.json()['matches']
        self.assertIsInstance(matches, list)
        for match in matches:
            self.assertIsInstance(match, dict)
            self.assertTrue({'name','score'} == set(match.keys()))


    def test_async_authorized_upload(self):
        """
        Test uploading an image with valid login credentials.
        """
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        with open(self.valid_image_file, "rb") as file:
            async_response = requests.post(self.web_server_base_url + "classify_image",
                                            files={"image": file},
                                            data={'method': 'async'},
                                            cookies=login_response.cookies)
        
        self._resp_is_json(async_response)
        self.assertIn("request_id", async_response.json())
        self.assertEqual(202, async_response.status_code)
   

    def test_async_upload(self):
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)
    
        with open(self.valid_image_file, "rb") as file:
            async_response = requests.post(self.web_server_base_url + "classify_image",
                                            files={"image": file},
                                            data={'method': 'async'},
                                            cookies=login_response.cookies)
        self.assertEqual(async_response.status_code, 202)

        data = async_response.json()
        request_id = data['request_id']

        for _ in range(10):  # Polling 10 times with a 2s interval
            async_response = requests.post(self.web_server_base_url + f'result/{str(request_id)}',
                                            cookies=login_response.cookies)
            result_data = async_response.json()

            if result_data['status'] == 'completed':
                self.assertIn('matches', result_data)
                break
            time.sleep(2)
        else:
            self.fail("Asynchronous classification did not complete in time.")


    def test_unauthorized_upload(self):    
        """
        Test uploading an image without logging in.
        """  
        for method in ['sync', 'async']:
            with open(self.valid_image_file, "rb") as file:
                response = requests.post(self.web_server_base_url + "classify_image",
                                            files={"image": file},
                                            data={'method': method})
            self._resp_is_json(response)
            self.assertEqual(400, response.status_code)


    def test_invalid_image_upload(self):
        """
        Test uploading an invalid image file with valid login credentials.
        """
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        for method in ['sync', 'async']:
            with open(self.invalid_image_file, "rb") as file:
                response = requests.post(self.web_server_base_url + "classify_image",
                                         files={"image": file}, 
                                         data={'method': method},
                                         cookies=login_response.cookies)
            
            self._resp_is_json(response)
            self.assertEqual(400, response.status_code)
    

    def test_missing_image(self):
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)
        
        for method in ['sync', 'async']:
            response = requests.post(self.web_server_base_url + "classify_image",
                                files={"image": ''}, 
                                data={'method': method},
                                cookies=login_response.cookies)
            
            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())


    # def test_status(self):
    #     """
    #     Test the status page format
    #     """
    #     response = requests.get(self.web_server_base_url + "status")
    #     self._resp_is_json(response)
    #     self.assertEqual(200, response.status_code)
    #     self.assertIn("status", response.json())
        
    #     status_dict = response.json()['status']
    #     self.assertIsInstance(status_dict, dict)

    #     self.assertIn("api_version", status_dict)
    #     self.assertIn("health", status_dict)
    #     self.assertIn("processed", status_dict)
    #     self.assertIn("uptime", status_dict)
    #     self.assertIn("fail", status_dict['processed'])
    #     self.assertIn("queued", status_dict['processed'])
    #     self.assertIn("running", status_dict['processed'])
    #     self.assertIn("success", status_dict['processed'])

    #     self.assertIsInstance(status_dict['api_version'], (float, int))
    #     self.assertIsInstance(status_dict['health'], str)
    #     self.assertIsInstance(status_dict['processed'], dict)
    #     self.assertIsInstance(status_dict['uptime'], float)
    #     self.assertIsInstance(status_dict['processed']['fail'], int)
    #     self.assertIsInstance(status_dict['processed']['queued'], int)
    #     self.assertIsInstance(status_dict['processed']['running'], int)
    #     self.assertIsInstance(status_dict['processed']['success'], int)

    
if __name__ == "__main__":
    # with open('TestResults.txt', 'w') as f:
    #     runner = unittest.TextTestRunner(f, verbosity=2)
    #     unittest.main(testRunner=runner)

    unittest.main()