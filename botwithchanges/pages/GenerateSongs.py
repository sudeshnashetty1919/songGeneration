import os
import time
import requests
import json

class SoundOfMeme:
    def __init__(self):
        self.login_url = "https://testapi.soundofmeme.com/googlelogin"
        self.upload_url = "https://engine.soundofmeme.com/image"
        self.usersongs_url = "https://testapi.soundofmeme.com/usersongs"
        self.create_song_url = "https://engine.soundofmeme.com/create"
        self.access_token = None

    def login(self, name, email, picture_url):
        payload = {"name": name, "email": email, "picture": picture_url}
        try:
            response = requests.post(self.login_url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            if "access_token" in response_data:
                self.access_token = response_data["access_token"]
                print(f"Login successful! Access Token: {self.access_token}")
                return self.access_token
            else:
                print("Login failed! Access token not received.")
                return None
        except requests.exceptions.RequestException as e:
            print(f"API login failed: {e}")
            return None

    def fetch_slugs_for_uploaded_ids(self, uploaded_ids):
        if not self.access_token:
            print("Access token is missing!")
            return None

        base_url = "https://song.soundofmeme.com/"
        slugs = []
        page = 1

        while True:
            try:
                url = f"{self.usersongs_url}?page={page}"
                headers = {"Authorization": f"Bearer {self.access_token}"}
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                songs_response = response.json()

                if not songs_response.get("songs"):
                    print(f"No more songs found or invalid response on page {page}.")
                    break

                for song in songs_response["songs"]:
                    if song.get("song_id") in uploaded_ids:
                        slug = song.get("slug")
                        if slug:
                            full_url = f"{base_url}{slug}"
                            slugs.append(full_url)
                            print(f"Found slug for ID {song['song_id']}: {full_url}")
                        else:
                            print(f"Slug not found for ID {song['song_id']}.")
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching songs on page {page}: {e}")
                break

        return slugs

    def generate_song(self, prompt, publish=False):
        if not self.access_token:
            print("Access token is missing!")
            return None

        try:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            data = {"publish": "true" if publish else "false", "prompt": str(prompt)}
            print(f"Sending request to generate song with data: {data}")

            response = requests.post(self.create_song_url, json=data, headers=headers)

            # Ensure the response was successful before accessing data
            response.raise_for_status()

            # Now print the response data
            response_data = response.json()
            print(f"Song generated successfully: {response_data}")

            # Save the song information to a file
            file_name = "generated_song_info.json"
            with open(file_name, "w") as file:
                json.dump(response_data, file, indent=4)
            print(f"Song information stored in {file_name}")

            return response_data
        except requests.exceptions.RequestException as e:
            print(f"API song generation failed: {e}")
            return None

    def upload_image(self, file_path,prompt=1,publish=False):
        if not self.access_token:
            print("Access token is missing!")
            return None

        try:
            with open(file_path, "rb") as file:
                img_data = file.read()

            files = {"file": ("image.jpg", img_data, "image/jpeg")}
            data = {"publish": "true" if publish else "false","prompt": str(prompt)}
            headers = {"Authorization": f"Bearer {self.access_token}"}
            print(f"Sending data: {data}")

            response = requests.post(self.upload_url, data=data, files=files, headers=headers)
            response.raise_for_status()
            response_data = response.json()

            #print(f"Image uploaded successfully: {response_data}")
            return response_data
        except requests.exceptions.RequestException as e:
            print(f"API image upload failed: {e}")
            return None
        
    def upload_image_with_text(self, file_path, prompt, publish=False):
        """
        Upload an image with associated metadata (prompt, genre, publish status).

        :param file_path: Path to the image file to be uploaded.
        :param prompt: Text prompt for the image.
        :param genre: Genre for the image/song (default: "rock").
        :param publish: Boolean indicating whether to publish the upload immediately.
        :return: Parsed response data from the API or None if the upload fails.
        """
        if not self.access_token:
            print("Access token is missing!")
            return None

        try:
            # Read the image file as binary data
            with open(file_path, "rb") as file:
                img_data = file.read()

            # Prepare the form data
            files = {"file": ("image.jpg", img_data, "image/jpeg")}
            data = {
                "prompt": prompt,
                "publish": "true" if publish else "false"
            }
            headers = {"Authorization": f"Bearer {self.access_token}"}

            # Log the data being sent
            print(f"Sending data: {data}")

            # Make the POST request to upload the image
            response = requests.post(self.upload_url, data=data, files=files, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            response_data = response.json()

            # Log and return the API response
            print(f"Image uploaded successfully: {response_data}")
            return response_data
        except requests.exceptions.RequestException as e:
            print(f"API image upload failed: {e}")
            return None
