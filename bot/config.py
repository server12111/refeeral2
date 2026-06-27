from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str
    admin_ids: str = ""
    database_url: str = f"sqlite+aiosqlite:///{_PROJECT_ROOT / 'bot.db'}"

    admin_channel_id: str = ""
    payments_channel_id: str = ""
    payments_channel_link: str = ""

    tgrass_code: str = ""
    botohub_key: str = ""
    botohub_views_key: str = ""
    piarflow_key: str = ""

    bot_username: str = ""

    @property
    def admin_id_list(self) -> list[int]:
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
