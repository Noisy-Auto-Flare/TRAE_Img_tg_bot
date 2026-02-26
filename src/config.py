import os
import re
from typing import Optional, Union

from dotenv import load_dotenv


class Config:
    def __init__(self, token: str, channel_id: Union[int, str], db_path: str) -> None:
        self.token = token
        self.channel_id = channel_id
        self.db_path = db_path


def load_config(env_path: Optional[str] = None) -> Config:
    if env_path:
        load_dotenv(env_path)
    else:
        load_dotenv()

    token = os.getenv("TELEGRAM_TOKEN", "")
    raw_channel_id = os.getenv("CHANNEL_ID", "")
    db_path = os.getenv("DB_PATH", "./imgbot.sqlite")

    if not token:
        raise RuntimeError("TELEGRAM_TOKEN не задан в окружении (.env)")
    if not raw_channel_id:
        raise RuntimeError("CHANNEL_ID не задан в окружении (.env)")

    t = raw_channel_id.strip()
    if re.fullmatch(r"-?\d{5,}", t):
        channel_id: Union[int, str] = int(t)
    else:
        channel_id = t

    return Config(token=token, channel_id=channel_id, db_path=db_path)
