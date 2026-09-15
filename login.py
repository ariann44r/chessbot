# -*- coding: utf-8 -*-
"""One-time YouTube OAuth login. Saves token.pickle so future runs need no login."""
import os, pickle
from google_auth_oauthlib.flow import InstalledAppFlow

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

flow = InstalledAppFlow.from_client_secrets_file(
    os.path.join(HERE, "client_secrets.json"), SCOPES)
creds = flow.run_local_server(port=0)
with open(os.path.join(HERE, "token.pickle"), "wb") as f:
    pickle.dump(creds, f)
print("Login saved to token.pickle ✅  (uploads now work without login)")
