"""Nemo Tracker — Configuration (DEVELOPMENT — local only, DO NOT COMMIT .env)"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Marzban
    marzban_url: str = "https://vpn.dealflow.bond"
    marzban_admin_username: str = "nedopekin"
    marzban_admin_password: str = ""

    # Database
    database_url: str = "postgresql+asyncpg://nemo_tracker:changeme@localhost:5432/nemo_tracker"

    # Telegram
    bot_token: str = ""
    admin_ids: str = ""

    # Web
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    web_secret_key: str = "change-this"

    # Tracking
    device_check_interval: int = 60
    auto_block_on_limit: bool = True
    notify_on_new_device: bool = True
    notify_on_limit_exceeded: bool = True

    # GeoIP
    geoip_db_path: str = "./data/GeoLite2-City.mmdb"

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
