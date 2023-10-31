from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv
import os


def msg(chat_msg):
    load_dotenv()
    # Create a slack client
    client = WebClient(token=os.environ.get('SLACK_TOKEN_SECRET'))

    # Post a message to a channel
    try:
        response = client.chat_postMessage(channel='#space-logs', text=chat_msg)
        assert response["message"]["text"] == chat_msg
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")
