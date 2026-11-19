"""Read-only Tauron CSV transport using mlesniew/elicznik."""
import csv
import math
import re
from urllib.parse import urlparse
from elicznik import ELicznikCSV
from elicznik.session import Session


class EnergyLoginError(RuntimeError):
    pass


class TauronClient(ELicznikCSV):
    # The upstream login currently has no request timeouts. Keep the same
    # Keycloak flow, with bounded I/O and validation before sending credentials.
    def login(self):
        self.session = Session()
        original = self.session.request
        def request(*args, **kwargs):
            kwargs.setdefault("timeout", (10, 40))
            response = original(*args, **kwargs)
            response.raise_for_status()
            return response
        self.session.request = request
        response = self.session.get(self.LOGIN_URL, params={
            "service": "https://elicznik.tauron-dystrybucja.pl"})
        match = re.search(r'<form[^>]+id="kc-form-login"[^>]+action="([^"]+)"', response.text)
        if not match:
            raise EnergyLoginError("Login form unavailable")
        url = match.group(1).replace("&amp;", "&")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".tauron-dystrybucja.pl"):
            raise EnergyLoginError("Unexpected login host")
        response = self.session.post(url, data={"username": self.username,
            "password": self.password, "credentialId": ""})
        if 'id="kc-form-login"' in response.text:
            raise EnergyLoginError("Login rejected")
        if self.site:
            self.session.post("https://elicznik.tauron-dystrybucja.pl/ustaw_punkt",
                              data={"site[client]": self.site})

    def consumption(self, start, end):
        # Retain repeated autumn DST hours: upstream get_readings() collapses
        # them in a dict. Use its CSV transport and timestamp parser instead.
        return parse_consumption(self._get_raw_data(start, end), start, end)


def parse_consumption(lines, start, end):
    reader = csv.DictReader(lines, delimiter=";")
    if not {"Data", "Rodzaj", " Wartość "}.issubset(reader.fieldnames or []):
        raise ValueError("Unexpected Tauron CSV format")
    result = []
    for row in reader:
        if row["Rodzaj"].replace(" [kWh]", "").strip() != "pobór":
            continue
        timestamp = ELicznikCSV._parse_timestamp(row["Data"])
        if not start <= timestamp.date() <= end:
            continue
        value = float(row[" Wartość "].replace(",", "."))
        if not math.isfinite(value) or value < 0:
            raise ValueError("Invalid consumption")
        result.append([timestamp.isoformat(), value])
    if not result:
        raise ValueError("No consumption readings")
    return sorted(result, key=lambda row: row[0])


class ELicznikAdapter:
    def __init__(self, username, password, site=None):
        self.username, self.password, self.site = username, password, site

    def fetch(self, start, end):
        client = TauronClient(self.username, self.password, self.site)
        try:
            client.login()
            return client.consumption(start, end)
        finally:
            if hasattr(client, "session"):
                client.session.close()
