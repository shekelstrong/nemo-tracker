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

    # Device tracking rules (user configurable)
    track_inbounds: str = "vless-reality-whitelist"  # comma-separated inbound tags to track
    ignore_inbounds: str = "vless-reality-standard"  # never track these
    ignored_ips: str = ""  # comma-separated IPs to ignore (proxy servers)
    only_enforce_with_limit: bool = True  # only enforce on users with device_count > 0

    # GeoIP
    geoip_db_path: str = "./data/GeoLite2-City.mmdb"

    @property
    def admin_ids_list(self) -> List[int]:
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    @property
    def track_inbounds_list(self) -> List[str]:
        return [x.strip() for x in self.track_inbounds.split(",") if x.strip()]

    @property
    def ignore_inbounds_list(self) -> List[str]:
        return [x.strip() for x in self.ignore_inbounds.split(",") if x.strip()]

    @property
    def ignored_ips_set(self) -> set:
        return {x.strip() for x in self.ignored_ips.split(",") if x.strip()}

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
