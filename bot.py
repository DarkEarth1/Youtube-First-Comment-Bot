import httplib2
import os
import sys
import time
import datetime
import json

from apiclient.discovery import build_from_document
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

# ======== Configure the following variables ===========
# Channel IDs
channels = ["UCfznY5SlSoZoXN0-kBPtCdg", "UCBIVKUsOGwCg8RNpucEGp_g", "UCzTTYntJHARp5YCxakwUepA"]
# Comment template
comment_template = "Jour {} où je demande à Fuze d'ouvrir Palanarchy"
# Time interval in seconds for checking new videos
interval = 100 

CLIENT_SECRETS_FILE = "./client_secrets.json"
YOUTUBE_READ_WRITE_SSL_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0
To make this sample run you will need to populate the client_secrets.json file
found at:
   %s
with information from the APIs Console
https://console.developers.google.com
For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
""" % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                   CLIENT_SECRETS_FILE))

def get_authenticated_service(args):
    flow = flow_from_clientsecrets(CLIENT_SECRETS_FILE, scope=YOUTUBE_READ_WRITE_SSL_SCOPE,
                                   message=MISSING_CLIENT_SECRETS_MESSAGE)
    storage = Storage("%s-oauth2.json" % sys.argv[0])
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        credentials = run_flow(flow, storage, args)
    with open("youtube-v3-discoverydocument.json", "r") as f:
        doc = f.read()
        return build_from_document(doc, http=credentials.authorize(httplib2.Http()))

def insert_comment(youtube, parent_id, text):
    insert_result = youtube.commentThreads().insert(
        part="snippet",
        body={
            "snippet": {
                "videoId": parent_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": text
                    }
                }
            }
        }
    )
    response = insert_result.execute()
    print("comment added")

def lastvideo(youtube, cid):
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=cid,
        maxResults=1
    )
    response = request.execute()
    return response["items"][0]["snippet"]["resourceId"]["videoId"]

def get_today_comment_index():
    try:
        with open('comment_index.json', 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {"last_date": "", "index": 0}

    today = datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=1))).strftime('%Y-%m-%d')

    if data["last_date"] != today:
        data["last_date"] = today
        data["index"] += 1
        with open('comment_index.json', 'w') as f:
            json.dump(data, f)

    return data["index"]

def main():
    argparser.add_argument("--text", help="Required; text that will be used as comment.")
    args = argparser.parse_args()
    youtube = get_authenticated_service(args)

    # Track last video IDs to avoid duplicate comments
    last_video_ids = {cid: None for cid in channels}

    while True:
        index = get_today_comment_index()
        comment = comment_template.format(index)

        for cid in channels:
            try:
                lastvid = lastvideo(youtube, cid)
                if lastvid != last_video_ids[cid]:
                    insert_comment(youtube, lastvid, comment)
                    last_video_ids[cid] = lastvid
                    print(f"Comment Inserted on channel {cid}")
            except HttpError as e:
                print(f"An HTTP error {e.resp.status} occurred:\n{e.content}")
            except Exception as e:
                print(f"An error occurred: {str(e)}")

        time.sleep(interval)
        print(f"Waiting for {interval} seconds before checking again...")

if __name__ == "__main__":
    main()
