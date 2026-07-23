from django.conf import settings
import requests

def exchange_code(code: str) -> dict:
        TOKEN_URL = "https://oauth2.googleapis.com/token"

        payload = {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": "postmessage",
            "grant_type": "authorization_code",
        }
        response = requests.post(TOKEN_URL, data=payload)
        response.raise_for_status()  # raise on 400/401 from Google
        return response.json()