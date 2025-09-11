#!/usr/bin/env python3
import os, ssl, certifi, logging
from datetime import datetime
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_message(data: Any) -> str:
    return f"*BIA-study-tracker-report - {datetime.now().strftime("%d %b %Y - %H:%M")}*\n```{data}```"


class SlackReportBot:
    def __init__(self) -> None:
        # Get Slack token from environment variable
        self.slack_token = os.getenv('SLACK_BOT_TOKEN')
        self.slack_channel = os.getenv('SLACK_CHANNEL')
        ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        self.client = WebClient(token=self.slack_token, ssl=ssl_ctx)

    def send_message(self, message: str) -> bool:
        try:
            self.client.chat_postMessage(channel=self.slack_channel, text=message, mrkdwn=True)
            logger.info(f"💬 Message sent to {self.slack_channel}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False

    def upload_file(self, file_path: str, message: str = "") -> bool:
        try:
            resp = self.client.files_upload_v2(channel=self.slack_channel, initial_comment=message, file=file_path)
            logger.info(f"📎 Uploaded {resp['file']['name']} to {self.slack_channel}")
            return True
        except SlackApiError as e:
            logger.error(f"Slack API error: {e.response['error']}")
            return False

    def run(self, data: Any, file_path: str | None = None) -> bool:
        msg = build_message(data)
        return self.upload_file(file_path, msg) if file_path else self.send_message(msg)
