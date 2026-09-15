# -*- coding: utf-8 -*-
"""YouTube upload via OAuth (NO password stored anywhere).
First run: a browser window opens -> login once -> token saved locally."""
import os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly"]

def get_uploaded_puzzle_ids(yt, max_pages=4):
    """Collect puzzle ids from our channel's recent video descriptions
    (the anti-duplicate memory that survives VPS wipes)."""
    ids = set()
    try:
        ch = yt.channels().list(part="contentDetails", mine=True).execute()
        up = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        page = None
        for _ in range(max_pages):
            pl = yt.playlistItems().list(part="snippet", playlistId=up,
                                         maxResults=50, pageToken=page).execute()
            for it in pl.get("items", []):
                desc = it["snippet"]["description"]
                for line in desc.splitlines():
                    if line.startswith("Puzzles:"):
                        ids.update(x.strip() for x in line.split(":", 1)[1].split(",") if x.strip())
            page = pl.get("nextPageToken")
            if not page: break
    except Exception:
        pass
    return ids
CLIENT_SECRETS = os.path.join(HERE, "client_secrets.json")
TOKEN = os.path.join(HERE, "token.pickle")

def get_service():
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    creds = None
    if os.path.exists(TOKEN):
        with open(TOKEN, "rb") as f: creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CLIENT_SECRETS):
                raise FileNotFoundError(
                    "client_secrets.json not found! See SETUP.md -> step 3.\n"
                    "TIP: if you logged in once on another PC, copy its "
                    "token.pickle next to this script - no login needed.")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN, "wb") as f: pickle.dump(creds, f)
    return build("youtube", "v3", credentials=creds)

def upload(video_path, title, description, tags, is_short=False):
    from googleapiclient.http import MediaFileUpload
    yt = get_service()
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:4900],
            "tags": tags,
            "categoryId": "20",  # Gaming
        },
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=8*(1<<20), resumable=True,
                            mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"    upload {int(status.progress()*100)}%", flush=True)
    vid = resp["id"]
    print(f"    UPLOADED: https://youtu.be/{vid}", flush=True)
    return vid

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python upload_youtube.py <video.mp4> [title]")
    else:
        upload(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "Chess Puzzle",
               "Test upload", ["chess", "puzzle"])
