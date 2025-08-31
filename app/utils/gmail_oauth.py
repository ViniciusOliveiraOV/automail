import os
from urllib.parse import urlencode

from flask import url_for

# Minimal helpers to construct the OAuth2 consent URL for Gmail (Google APIs).
# This module does not store tokens; the endpoint will exchange the code and
# you must persist the refresh token in a secret or database.

CLIENT_ID = os.environ.get("GMAIL_OAUTH_CLIENT_ID")
CLIENT_SECRET = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET")
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def build_consent_url(state: str = "") -> str:
    redirect_uri = url_for("gmail_auth.oauth_callback", _external=True)
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
