import unittest
import requests
import time

class ImageUploadAPITest(unittest.TestCase):
    """
    Test suite for the Image Upload API.
    This suite tests various endpoints of an image upload service including login, image upload,
    and user management such as authorized and unauthorized uploads.
    """
    def setUp(self):
        """
        Set up test variables and URLs. This method runs before each test case.
        Initializes base URLs for the web server and image API, along with paths for valid and invalid test images.
        """
        self.web_server_base_url = f'http://127.0.0.1:8000/'
        self.image_api_base_url = f'http://127.0.0.1:8000/'
        self.valid_image_file = "uploads/dog.jpg"
        self.invalid_image_file = "uploads/invalid_image.txt"
        self.login_data = {"username": "admin", "password": "Aa123"}

    def _resp_is_json(self, response):
        """
        Helper method to check if the response content is in JSON format.
        :param response: Response object to check.
        """
        self.assertEqual("application/json", response.headers.get("Content-Type", ""))

    def test_sync_authorized_upload(self):
        """
        Test case for uploading a valid image using synchronous method with valid login credentials.
        Verifies that the classification result contains expected fields and a successful status code (200).
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
            self.assertTrue({'name', 'score'} == set(match.keys()))

    def test_async_authorized_upload(self):
        """
        Test case for uploading a valid image using asynchronous method with valid login credentials.
        Verifies that a request ID is returned, and the status code is 202 (Accepted).
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
        """
        Test case for uploading a valid image using asynchronous method and polling the result until completion.
        Polls the result endpoint multiple times to check for classification result.
        """
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

        for _ in range(10):
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
        Test case for uploading an image without logging in.
        Verifies that an error message is returned with status code 400 (Bad Request).
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
        Test case for uploading an invalid file format (non-image file) with valid login credentials.
        Verifies that the server returns a 400 status code.
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
        """
        Test case for submitting a request without providing an image file.
        Verifies that the server returns a 400 status code with an appropriate error message.
        """
        login_response = requests.post(self.web_server_base_url + "login", data=self.login_data, allow_redirects=False)
        self.assertEqual(302, login_response.status_code)

        for method in ['sync', 'async']:
            response = requests.post(self.web_server_base_url + "classify_image",
                                     files={"image": ''},
                                     data={'method': method},
                                     cookies=login_response.cookies)

            self.assertEqual(response.status_code, 400)
            self.assertIn('error', response.json())


if __name__ == "__main__":
    unittest.main()
