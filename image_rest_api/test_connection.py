import requests 
import json 
PORT = 8000  
IP = "10.0.0.6"

valid_image_file = rf"C:\Users\maaya\MLops_project\web_server\uploads\dog.jpg"
base_url = f"http://{IP}:{PORT}/"

# with open(valid_image_file, "rb") as file:
#     response = requests.post(base_url + "upload_image", files={"image": file})
# print(response.json())

with open(valid_image_file, "rb") as file:
    response = requests.post(base_url + "async_upload", files={"image": file})
print(response.json())