import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

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
    )