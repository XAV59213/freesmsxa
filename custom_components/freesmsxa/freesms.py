"""Mock FreeClient class for Free Mobile SMS API (replace with actual implementation)."""

import requests
from http import HTTPStatus

class FreeClient:
    """Client for Free Mobile SMS API."""
    
    def __init__(self, username, access_token):
        self._username = username
        self._access_token = access_token
        self._base_url = "https://smsapi.free-mobile.fr/sendmsg"
    
    def send_sms(self, message):
        """Send an SMS via Free Mobile API."""
        params = {
            "user": self._username,
            "pass": self._access_token,
            "msg": message
        }
        return requests.get(self._base_url, params=params)
