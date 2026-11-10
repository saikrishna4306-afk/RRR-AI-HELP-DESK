
import os
import requests
from dotenv import load_dotenv

# Load values from the project's .env file
load_dotenv()

api_key = os.getenv("GNANI_API_KEY")

if not api_key:
    raise ValueError("GNANI_API_KEY was not loaded from .env")

print("Gnani API key loaded:", bool(api_key))
print("API key length:", len(api_key))

url = "https://api.vachana.ai/stt/v3"

with open("test.wav", "rb") as audio:
    response = requests.post(
        url,
        headers={"X-API-Key-ID": api_key},
        data={
            "language_code": "te-IN",
            "preferred_language": "te-IN",
            "format": "transcribe",
        },
        files={
            "audio_file": ("test.wav", audio, "audio/wav")
        },
        timeout=60,
    )

print("HTTP Status:", response.status_code)
print("Response:", response.text)
