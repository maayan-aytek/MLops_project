import os
import io
import sys
import time
import random
import unittest
import requests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..')))
from shared.constants import LOCAL_IP, IMAGE_API_PORT, TEST_PREFIX_UPLOADS_PATH


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
        self.image_api_base_url = f'http://{LOCAL_IP}:{IMAGE_API_PORT}/'
        self.valid_image_file = f"{TEST_PREFIX_UPLOADS_PATH}/dog.jpg"
        self.invalid_image_file = f"{TEST_PREFIX_UPLOADS_PATH}/invalid_image.txt"


    def _resp_is_json(self, response):
        """
        Helper method to check if the response content is in JSON format.
        :param response: Response object to check.
        """
        self.assertEqual("application/json", response.headers.get("Content-Type", ""))


    def _check_error_structure(self, response_data):
        """
        Helper function to validate the structure of an error response.
        Verifies that the response contains the expected 'error' key with 'message' and 'code'.
        """
        self.assertIn('error', response_data)
        self.assertIn('message', response_data['error'])
        self.assertIn('code', response_data['error'])
        self.assertIsInstance(response_data['error']['message'], str)
        self.assertIsInstance(response_data['error']['code'], int)

    
    def _check_match_structure(self, matches):
        """
        Helper function to validate the structure of 'matches' in the image classification response.
        Verifies that the 'matches' list contains dictionaries with 'name' and 'score' keys.
        """
        self.assertIsInstance(matches, list)
        for match in matches:
            self.assertIsInstance(match, dict)
            self.assertTrue({'name', 'score'} == set(match.keys()))
            self.assertIsInstance(match['name'], str)
            self.assertIsInstance(match['score'], (int, float))


    def test_sync_upload_image(self):
        """
        Test uploading a valid image synchronously.
        Verifies the classification result and that the status code is 200.
        """
        with open(self.valid_image_file, "rb") as file:
            sync_response = requests.post(self.image_api_base_url + "upload_image",
                                        files={"image": file})
        result_data = sync_response.json()
        self._resp_is_json(sync_response)
        self.assertIn("matches", result_data)
        self.assertEqual(200, sync_response.status_code)

        self._check_match_structure(result_data["matches"])


    def test_async_request(self):
        """
        Test case for uploading a valid image using asynchronous method.
        Verifies that a request ID is returned, and the status code is 202 (Accepted).
        """
        with open(self.valid_image_file, "rb") as file:
            async_response = requests.post(self.image_api_base_url + "async_upload",
                                           files={"image": file})

        self._resp_is_json(async_response)
        self.assertIn("request_id", async_response.json())
        self.assertEqual(202, async_response.status_code)


    def test_async_upload(self):
        """
        Test case for uploading a valid image using asynchronous method and polling the result until completion.
        Polls the result endpoint multiple times to check for classification result.
        """

        with open(self.valid_image_file, "rb") as file:
            async_response = requests.post(self.image_api_base_url + "async_upload",
                                           files={"image": file})
        self.assertEqual(async_response.status_code, 202)

        data = async_response.json()
        request_id = data['request_id']

        for _ in range(10):
            time.sleep(2)
            async_response = requests.get(self.image_api_base_url + f'result/{str(request_id)}')
            result_data = async_response.json()

            if result_data['status'] == 'completed':
                self._resp_is_json(async_response)
                self.assertIn("matches", result_data)
                self._check_match_structure(result_data["matches"])
                break
        else:
            self.fail("Asynchronous classification did not complete in time.")


    def test_invalid_image_upload(self):
        """
        Test case for uploading an invalid file format (non-image file).
        Verifies that the server returns a 400 status code.
        """
        for endpoint in ['upload_image', 'async_upload']:
            with open(self.invalid_image_file, "rb") as file:
                response = requests.post(self.image_api_base_url + endpoint,
                                        files={"image": file})

            self._resp_is_json(response)
            response_data = response.json()
            self._check_error_structure(response_data)
            self.assertEqual(400, response.status_code)


    def test_missing_image(self):
        """
        Test sending a request without an image.
        Verifies the server returns a 400 status code.
        """
        for endpoint in ['upload_image', 'async_upload']:
            response = requests.post(self.image_api_base_url + endpoint,
                                    files={"image": None})
            self._resp_is_json(response)
            self.assertEqual(400, response.status_code)
            self._check_error_structure(response.json())


    def test_status(self):
        """
        Test checking the status endpoint.
        Verifies the API's uptime, health status, processed stats, and API version.
        """
        response = requests.get(self.image_api_base_url + "status")
        
        self._resp_is_json(response)
        self.assertEqual(200, response.status_code)
        
        status_data = response.json().get('status')
        self.assertIsInstance(status_data, dict)

        self.assertIn('health', status_data)
        self.assertIn(status_data['health'], ['ok', 'error'])
        
        self.assertIn('uptime', status_data)
        self.assertIsInstance(status_data['uptime'], (int, float))
        
        self.assertIn('processed', status_data)
        processed_data = status_data['processed']
        self.assertIsInstance(processed_data, dict)
        for key in ['success', 'fail', 'running', 'queued']:
            self.assertIn(key, processed_data)
            self.assertIsInstance(processed_data[key], int)

        self.assertIn('api_version', status_data)
        self.assertIsInstance(status_data['api_version'], (int, float))


    def test_result_not_found(self):
        """
        Test case for retrieving the result with an unknown request ID.
        Verifies that the server returns a 404 status code.
        """
        random_request_id = str(random.randint(10000, 1000000))
        result_response = requests.get(self.image_api_base_url + f'result/{random_request_id}')
        
        self.assertEqual(404, result_response.status_code)
        self._check_error_structure(result_response.json())
        self.assertEqual(result_response.json()['error']['message'], 'ID not found')


    def test_upload_sync_empty_file(self):
        """
        Test case for uploading empty image (sync mode)
        """
        response = requests.post(self.image_api_base_url + "upload_image", files={'image': ('empty_image.jpg', io.BytesIO(), 'image/jpeg')})
        self.assertEqual(response.status_code, 400)
        self._check_error_structure(response.json())


    def test_upload_async_empty_file(self):
        """
        Test case for uploading empty image (async mode)
        """
        response = requests.post(self.image_api_base_url + "async_upload", files={'image': ('empty_image.jpg', io.BytesIO(), 'image/jpeg')})
        self.assertEqual(response.status_code, 400)
        self._check_error_structure(response.json())


if __name__ == "__main__":
    unittest.main()
