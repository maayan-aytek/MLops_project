from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['username']
        self.username = user_data['username']
        self.first_name = user_data['first_name']
        self.password = user_data['password']
        self.user_data = user_data

    def get_id(self):
        return self.username