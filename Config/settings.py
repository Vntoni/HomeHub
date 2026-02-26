import os
import sys
from dataclasses import dataclass
from dotenv import load_dotenv
from pathlib import Path

# Szukaj .env w kilku miejscach (kolejność: binary dir → home → projekt)
# sys.executable wskazuje na binary gdy uruchamiamy z PyInstaller
_binary_dir = Path(sys.executable).parent          # obok BazaDomowa binary
_project_dir = Path(__file__).parent               # Config/ w projekcie deweloperskim
_home_config = Path.home() / ".config" / "bazadomowa" / ".env"  # ~/.config/bazadomowa/.env

for _env_path in [_binary_dir / ".env", _home_config, _project_dir / ".env"]:
    if _env_path.exists():
        load_dotenv(dotenv_path=_env_path)
        break

@dataclass
class Settings:
    airstage_country: str
    salon_id: str
    jadalnia_id: str
    user: str
    pwd: str
    ariston_pwd: str
    ariston_device_id: str
    washer_poll_seconds: int
    # Cozy Touch heaters
    cozytouch_user: str = ""
    cozytouch_pwd: str = ""
    cozytouch_scope: str = ""
    locale: str = "pl-PL"

def get_settings() -> Settings:
    return Settings(
        airstage_country=os.getenv("AIRSTAGE_COUNTRY", "PL"),
        salon_id=os.environ["AC_SALON_ID"],
        jadalnia_id=os.environ["AC_JADALNIA_ID"],
        user=os.environ["AIRSTAGE_USER"],
        pwd=os.environ["AIRSTAGE_PWD"],
        ariston_pwd=os.environ["ARISTON_PWD"],
        ariston_device_id=os.environ["ARISTON_DEVICE_ID"],
        washer_poll_seconds=os.environ["WASHER_POLL_SECONDS"],
        cozytouch_user=os.getenv("COZYTOUCH_USER", ""),
        cozytouch_pwd=os.getenv("COZYTOUCH_PWD", ""),
        cozytouch_scope=os.getenv("COZYTOUCH_SCOPE", "openid"),
    )