from pathlib import Path
import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("__main__." + __name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[
            str(Path(__file__).parents[1] / ".env_template"),
            str(Path(__file__).parents[1] / ".env"),
        ],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'
    )

    public_search_api: str = Field("")
    public_website_url: str = Field("")
    public_mongo_api: str = Field("")
    slack_bot_token: str = Field("")
    slack_channel: str = Field("")

def get_settings():
    return Settings()