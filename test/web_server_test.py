import unittest
import requests


class WebServerTest(unittest.TestCase):
    """
    Test suite for the web server routes using the `requests` library.
    Tests the behavior of various endpoints for both authenticated and unauthenticated users.
    """

    def setUp(self):
        """
        Set up test variables and URLs.
        This method runs before each test case.
        """
        self.base_url = 'http://127.0.0.1:8000/'  # URL where your Flask app is running
        self.login_url = f'{self.base_url}login'
        self.choose_action_url = f'{self.base_url}choose_action'
        self.home_url = f'{self.base_url}home'
        self.about_us_url = f'{self.base_url}about_us'
        
        # Example valid user credentials
        self.valid_credentials = {'username': 'admin', 'password': 'Aa123'}


    def _login(self):
        """
        Helper method to log in a user and return the response.
        """
        response = requests.post(self.login_url, data=self.valid_credentials, allow_redirects=False)
        self.assertEqual(302, response.status_code)
        return response.cookies


    def test_authenticated_user_redirection(self):
        """
        Test that an authenticated user is redirected to /choose_action when accessing '/'.
        """
        # Log in the user
        cookies = self._login()
        
        # Access the home route with authentication cookies
        response = requests.get(self.base_url, cookies=cookies, allow_redirects=False)
                
        self.assertEqual(response.status_code, 302)
        self.assertIn('/choose_action', response.headers['Location'], "Authenticated user was not redirected to /choose_action.")


    def test_unauthenticated_user_redirection(self):
        """
        Test that an unauthenticated user is redirected to /home when accessing '/'.
        """
        response = requests.get(self.base_url, allow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/home', response.headers['Location'])


    def test_home_view_render(self):
        """
        Test that the /home route renders the home view correctly.
        """
        response = requests.get(self.home_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h1>Welcome to CustomTales!</h1>', response.text)


    def test_about_us_render(self):
        """
        Test that the /about_us route renders the about us page correctly.
        """
        response = requests.get(self.about_us_url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('<h3>An interactive storytelling platform, where creativity meets personalization.</h3>', response.text)


    def test_choose_action_authenticated(self):
        """
        Test that an authenticated user can access /choose_action.
        """
        cookies = self._login()
        
        response = requests.get(self.choose_action_url, cookies=cookies)
        
        self.assertEqual(response.status_code, 200, "Authenticated user could not access /choose_action.")
        self.assertIn('<h1>What would you like to do?</h1>', response.text)


    def test_choose_action_unauthenticated(self):
        """
        Test that an unauthenticated user is redirected to /login when accessing /choose_action.
        """
        response = requests.get(self.choose_action_url)
        self.assertEqual(response.status_code, 400)


    def test_non_existent_route(self):
        """
        Test accessing a non-existent route results in a 404 status code.
        """
        response = requests.get(f'{self.base_url}non_existent_route')
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
