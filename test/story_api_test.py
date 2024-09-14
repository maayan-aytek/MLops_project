import unittest
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class RoomStoryTest(unittest.TestCase):
    def setUp(self):
        self.base_url = 'http://127.0.0.1:8000/'

        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.signup_data = {
            'username': 'new_user_test_story_api',
            'password': 'Password1!',
            'name': 'Test User',
            'gender': 'male',
            'age': 10,
            'interests': 'sports, animals'
        }
        self.qa = {
            "Moral of the story": "be kind",
            "Main charcter name": "ori",
            "Secondery charcter name": "or",
            "Story mode": "creative",
            "Story inspiration": "Ignore"
        }

    def test_story_generation(self):
        driver = self.driver
        wait = WebDriverWait(driver, 10)

        driver.get(self.base_url + 'sign_up')

        driver.find_element(By.NAME, 'username').send_keys(self.signup_data['username'])
        driver.find_element(By.NAME, 'password1').send_keys(self.signup_data['password'])
        driver.find_element(By.NAME, 'password2').send_keys(self.signup_data['password'])
        driver.find_element(By.NAME, 'name').send_keys(self.signup_data['name'])
        driver.find_element(By.NAME, 'gender').send_keys(self.signup_data['gender'])
        driver.find_element(By.NAME, 'age').send_keys(str(self.signup_data['age']))
        driver.find_element(By.NAME, 'interests').send_keys(self.signup_data['interests'])

        driver.find_element(By.XPATH, "//button[text()='Register']").click()

        wait.until(EC.url_contains('choose_action'))
        driver.get(self.base_url + 'handle_room_request')

        driver.find_element(By.XPATH, "//li[contains(text(), 'Create a Room')]").click()
        driver.find_element(By.NAME, 'nickname').send_keys('TestNickname')
        driver.find_element(By.NAME, 'participants').send_keys('1')
        driver.find_element(By.XPATH, "//button[text()='Create Room']").click()

        wait.until(EC.url_contains('lobby'))

        driver.get(self.base_url + 'room')

        for q, a in self.qa.items:
            wait.until(EC.visibility_of_element_located((By.ID, 'current-question')))
            answer_box = driver.find_element(By.CLASS_NAME, 'text-input')
            answer_box.send_keys(a)
            submit_button = driver.find_element(By.CLASS_NAME, 'submit-btn')
            submit_button.click()
            time.sleep(1)


        wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'story-box')))
        story_title = driver.find_element(By.CLASS_NAME, 'story-box').find_element(By.TAG_NAME, 'h2').text
        self.assertIn("Your Story Title", story_title)  # Modify this based on expected title content
        
    def tearDown(self):
        self.driver.quit()

if __name__ == "__main__":
    unittest.main()