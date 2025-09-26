import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Replace with your Slack webhook URL
def load_secrets(path="secrets.txt"):
    secrets = {}
    with open(path, "r") as f:
        for line in f:
            if "=" in line:
                key, value = line.strip().split("=", 1)
                secrets[key] = value
    return secrets
secrets = load_secrets()

SLACK_BOT_TOKEN = secrets["SLACK_BOT_TOKEN"]
SLACK_WEBHOOK_URL = secrets["SLACK_WEBHOOK_URL"]
SLACK_CHANNEL = "C09J10VQ02C" 

# ✅ Setup logging
logging.basicConfig(level=logging.INFO)

# ✅ Initialize Slack WebClient
client = WebClient(token=SLACK_BOT_TOKEN)

def send_slack_message(message, channel_id):
    """Send a message to a specific Slack channel by channel ID."""
    try:
        response = client.chat_postMessage(
            channel=channel_id,
            text=message
        )
        if response["ok"]:
            logging.info(f"✅ Message sent to {channel_id}")
    except SlackApiError as e:
        logging.error(f"❌ Slack API Error: {e.response['error']}")

send_slack_message("Hello from the actuator-dispenser!", SLACK_CHANNEL)