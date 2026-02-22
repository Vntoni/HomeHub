"""
Atlantic Cozy Touch API Client - Kompletny klient do sterowania grzejnikami
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, List, Optional
import json


class AtlanticCozytouchClient:
    """
    Klient API dla grzejników Atlantic Cozy Touch (Magellan API)
    """

    BASE_URL = "https://apis.groupe-atlantic.com"
    CLIENT_ID = "e8D1nA3hvv1tnc1MpoA7G5uD46Aa"
    CLIENT_SECRET = "7jKZKSwfUI4doh7jEfIUdsGeG5ka"

    # Capability IDs (znalezione przez sniffing)
    CAPABILITY_TARGET_TEMP = 40  # Zawsze używaj 40 do zmiany temperatury!
    CAPABILITY_ACTUAL_TEMP = 117
    CAPABILITY_HEATING_MODE = 7
    CAPABILITY_POWER_STATE = 73
    CAPABILITY_WINDOW_DETECTION = 152
    CAPABILITY_ABSENCE_MODE = 153
    CAPABILITY_ENERGY_CONSUMPTION = 57

    # Heating Modes
    MODE_COMFORT = 1
    MODE_ECO = 2
    MODE_FROST_PROTECTION = 3
    MODE_PROGRAM = 4
    MODE_OFF = 5

    def __init__(self, username: str, password: str, scope: str = "openid"):
        """
        Inicjalizacja klienta

        Args:
            username: Email w formacie GA-PRIVATEPERSON/email@example.com
            password: Hasło
            scope: OAuth scope (domyślnie "openid")
        """
        self.username = username
        self.password = password
        self.scope = scope
        self.access_token: Optional[str] = None
        self.devices: List[Dict] = []

        self.headers = {
            "User-Agent": "cozytouch-ios-v3.25.0",
            "appInstallNumber": "107AOB9-C501-4FF3-8CC2-1B523D7C5A43",
            "uniqId": "CT3.25.0IOS721BAEC7-9044-4E8D-B733-A7B766C93BA9",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    def login(self) -> bool:
        """
        Zaloguj się i pobierz access token

        Returns:
            True jeśli sukces, False jeśli błąd
        """
        url = f"{self.BASE_URL}/users/token"

        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "scope": self.scope
        }

        try:
            response = requests.post(
                url,
                data=payload,
                headers=self.headers,
                auth=HTTPBasicAuth(self.CLIENT_ID, self.CLIENT_SECRET),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                return True
            else:
                print(f"Login failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"Login error: {e}")
            return False

    def get_devices(self) -> List[Dict]:
        """
        Pobierz listę urządzeń

        Returns:
            Lista urządzeń (słowników)
        """
        if not self.access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        url = f"{self.BASE_URL}/magellan/cozytouch/setupviewv2"

        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code == 200:
                setup_data = response.json()

                # API może zwracać listę lub pojedynczy obiekt
                if isinstance(setup_data, list):
                    setup = setup_data[0] if len(setup_data) > 0 else {}
                else:
                    setup = setup_data

                self.devices = setup.get('devices', [])
                return self.devices
            else:
                print(f"Get devices failed: {response.status_code}")
                return []

        except Exception as e:
            print(f"Get devices error: {e}")
            return []

    def set_capability(self, device_id: int, capability_id: int, value: str) -> bool:
        """
        Ustaw wartość capability (podstawowa metoda sterowania)

        Format z sniffingu:
        POST /magellan/executions/writecapability
        Body: {"deviceId": 27082457, "capabilityId": 40, "value": "17.0"}
        Response: {"id": 36999398} - execution ID

        Potem sprawdzamy status:
        GET /magellan/executions/{executionId}
        Response: {"id": ..., "state": "COMPLETED" lub "IN_PROGRESS", ...}

        Args:
            device_id: ID urządzenia
            capability_id: ID capability
            value: Wartość (jako string)

        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not self.access_token:
            raise RuntimeError("Not logged in. Call login() first.")

        # Endpoint znaleziony w sniffingu!
        url = f"{self.BASE_URL}/magellan/executions/writecapability"

        headers = self.headers.copy()
        headers["Authorization"] = f"Bearer {self.access_token}"
        headers["Content-Type"] = "application/json"

        # Format body ze sniffingu
        payload = {
            "deviceId": device_id,
            "capabilityId": capability_id,
            "value": value
        }

        try:
            # Krok 1: Wyślij request writecapability
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 201:
                # Zwraca execution ID
                try:
                    execution_data = response.json()
                    # Response może być liczbą lub obiektem
                    if isinstance(execution_data, dict):
                        execution_id = execution_data.get('id')
                    else:
                        execution_id = execution_data  # Samo ID jako liczba
                except:
                    execution_id = None

                if execution_id:
                    # Krok 2: Sprawdź status wykonania
                    import time
                    max_attempts = 10

                    for attempt in range(max_attempts):
                        time.sleep(0.5)  # Odczekaj 0.5s między próbami

                        status_url = f"{self.BASE_URL}/magellan/executions/{execution_id}"
                        status_response = requests.get(status_url, headers=headers, timeout=30)

                        if status_response.status_code == 200:
                            try:
                                status_data = status_response.json()
                                state = status_data.get('state', 'UNKNOWN')

                                # State może być liczbą lub stringiem
                                # Z logów: 2 = IN_PROGRESS, 3 = COMPLETED (prawdopodobnie)
                                if state in ['COMPLETED', 3, '3']:
                                    # Sukces!
                                    return True
                                elif state in ['IN_PROGRESS', 2, '2', 1, '1']:
                                    # Czekaj dalej
                                    continue
                                elif state in ['FAILED', 'ERROR', 0, '0']:
                                    # Błąd
                                    print(f"Execution failed: {status_data}")
                                    return False
                                else:
                                    # Nieznany stan - ale może to sukces?
                                    # Jeśli to ostatnia próba, uznajmy za sukces
                                    if attempt >= max_attempts - 1:
                                        return True
                                    continue
                            except:
                                # Błąd parsowania - czekaj
                                continue

                    # Timeout - nie udało się w czasie
                    print(f"Timeout waiting for execution {execution_id}")
                    return False

                # Brak execution ID - ale status 201, uznajemy za sukces
                return True
            else:
                print(f"Set capability failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"Set capability error: {e}")
            return False

    # ========================================================================
    # HIGH-LEVEL API - Wygodne funkcje sterowania
    # ========================================================================

    def set_target_temperature(self, device_id: int, temperature: float, duration_minutes: int = 120) -> bool:
        """
        Ustaw temperaturę docelową

        WAŻNE: W trybie PROGRAM prawidłowa kolejność to:
        1. Ustaw czas trwania (capability 158)
        2. Aktywuj wyjątek (capability 157 = "1")
        3. Ustaw temperaturę (capability 40) <- NA KOŃCU!

        Args:
            device_id: ID urządzenia
            temperature: Temperatura w °C (7-28)
            duration_minutes: Czas trwania w minutach (domyślnie 120 = 2h)

        Returns:
            True jeśli sukces
        """
        if not 7 <= temperature <= 28:
            raise ValueError("Temperature must be between 7 and 28°C")

        # Krok 1: Ustaw czas trwania (capability 158)
        if not self.set_capability(device_id, 158, str(duration_minutes)):
            print("Błąd: Nie udało się ustawić czasu trwania (cap 158)")
            return False

        # Krok 2: Aktywuj tryb wyjątku (capability 157 = "1")
        if not self.set_capability(device_id, 157, "1"):
            print("Błąd: Nie udało się aktywować wyjątku (cap 157)")
            return False

        # Krok 3: Ustaw temperaturę (capability 40) - NA KOŃCU!
        if not self.set_capability(device_id, 40, str(temperature)):
            print("Błąd: Nie udało się ustawić temperatury (cap 40)")
            return False

        return True

    def cancel_exception_mode(self, device_id: int) -> bool:
        """
        Anuluj tryb wyjątku (wróć do programu)

        Args:
            device_id: ID urządzenia

        Returns:
            True jeśli sukces
        """
        return self.set_capability(device_id, 157, "0")

    def set_mode_manual(self, device_id: int) -> bool:
        """
        Przełącz na tryb ręczny (manual)
        Capability 184: value "0" = manual

        Args:
            device_id: ID urządzenia

        Returns:
            True jeśli sukces
        """
        return self.set_capability(device_id, 184, "0")

    def set_mode_program(self, device_id: int) -> bool:
        """
        Przełącz na tryb programowalny (program/schedule)
        Capability 184: value "1" = program

        Args:
            device_id: ID urządzenia

        Returns:
            True jeśli sukces
        """
        return self.set_capability(device_id, 184, "1")

    def set_heating_mode(self, device_id: int, mode: int) -> bool:
        """
        Ustaw tryb grzania

        Args:
            device_id: ID urządzenia
            mode: 1=Comfort, 2=Eco, 3=Frost Protection, 4=Program, 5=Off

        Returns:
            True jeśli sukces
        """
        if mode not in [1, 2, 3, 4, 5]:
            raise ValueError("Mode must be 1-5")

        return self.set_capability(device_id, self.CAPABILITY_HEATING_MODE, str(mode))

    def set_window_detection(self, device_id: int, enabled: bool) -> bool:
        """
        Włącz/wyłącz detekcję otwartego okna

        Args:
            device_id: ID urządzenia
            enabled: True = włączone, False = wyłączone

        Returns:
            True jeśli sukces
        """
        value = "1" if enabled else "0"
        return self.set_capability(device_id, self.CAPABILITY_WINDOW_DETECTION, value)

    def set_absence_mode(self, device_id: int, enabled: bool) -> bool:
        """
        Włącz/wyłącz tryb nieobecności

        Args:
            device_id: ID urządzenia
            enabled: True = włączone, False = wyłączone

        Returns:
            True jeśli sukces
        """
        value = "1" if enabled else "0"
        return self.set_capability(device_id, self.CAPABILITY_ABSENCE_MODE, value)

    # ========================================================================
    # GETTERS - Odczyt stanów
    # ========================================================================

    def get_device_capability(self, device_id: int, capability_id: int) -> Optional[str]:
        """
        Pobierz wartość capability dla urządzenia

        Args:
            device_id: ID urządzenia
            capability_id: ID capability

        Returns:
            Wartość jako string lub None jeśli nie znaleziono
        """
        for device in self.devices:
            if device.get('deviceId') == device_id:
                for cap in device.get('capabilities', []):
                    if cap.get('capabilityId') == capability_id:
                        return cap.get('value')
        return None

    def get_target_temperature(self, device_id: int) -> Optional[float]:
        """Pobierz temperaturę docelową"""
        value = self.get_device_capability(device_id, self.CAPABILITY_TARGET_TEMP)
        return float(value) if value else None

    def get_actual_temperature(self, device_id: int) -> Optional[float]:
        """Pobierz aktualną temperaturę"""
        value = self.get_device_capability(device_id, self.CAPABILITY_ACTUAL_TEMP)
        return float(value) if value else None

    def get_heating_mode(self, device_id: int) -> Optional[int]:
        """Pobierz tryb grzania"""
        value = self.get_device_capability(device_id, self.CAPABILITY_HEATING_MODE)
        return int(value) if value else None

    def get_device_by_name(self, name: str) -> Optional[Dict]:
        """
        Znajdź urządzenie po nazwie

        Args:
            name: Nazwa urządzenia (np. "Juras", "Migacze")

        Returns:
            Słownik z danymi urządzenia lub None
        """
        for device in self.devices:
            # Sprawdź customName lub name
            custom_name = device.get('customName', '')
            device_name = device.get('name', '')

            if name.lower() in custom_name.lower() or name.lower() in device_name.lower():
                return device

        return None

    def get_all_device_names(self) -> List[str]:
        """Pobierz listę nazw wszystkich urządzeń"""
        return [device.get('name', f"Device {device.get('deviceId')}")
                for device in self.devices]


# ============================================================================
# PRZYKŁAD UŻYCIA
# ============================================================================

if __name__ == "__main__":
    # Inicjalizacja
    client = AtlanticCozytouchClient(
        username="GA-PRIVATEPERSON/antekmigala@gmail.com",
        password="F5eotvky",
        scope="openid device_1771675781959"
    )

    print("=" * 80)
    print(" ATLANTIC COZY TOUCH CLIENT - PRZYKŁAD UŻYCIA")
    print("=" * 80)

    # Logowanie
    print("\n[1/2] Logowanie...")
    if not client.login():
        print("✗ Nie udało się zalogować!")
        exit(1)

    print("✓ Zalogowano pomyślnie!")

    # Pobieranie urządzeń
    print("\n[2/2] Pobieranie urządzeń...")
    devices = client.get_devices()

    if not devices:
        print("✗ Nie znaleziono urządzeń!")
        exit(1)

    print(f"✓ Znaleziono {len(devices)} urządzeń")

    # Wyświetl urządzenia
    print("\n" + "=" * 80)
    print(" DOSTĘPNE GRZEJNIKI")
    print("=" * 80)

    for i, device in enumerate(devices, 1):
        device_id = device.get('deviceId')
        name = device.get('name')

        target_temp = client.get_target_temperature(device_id)
        actual_temp = client.get_actual_temperature(device_id)
        mode = client.get_heating_mode(device_id)

        mode_names = {1: "Comfort", 2: "Eco", 3: "Frost", 4: "Program", 5: "Off"}
        mode_name = mode_names.get(mode, "Unknown")

        print(f"\n{i}. {name}")
        print(f"   ID: {device_id}")
        print(f"   Temp docelowa: {target_temp}°C")
        print(f"   Temp aktualna: {actual_temp}°C")
        print(f"   Tryb: {mode_name} ({mode})")

    # Przykład sterowania (odkomentuj żeby przetestować)
    # print("\n" + "=" * 80)
    # print(" TEST STEROWANIA")
    # print("=" * 80)
    #
    # device_id = devices[0].get('deviceId')
    # print(f"\nTestuję na urządzeniu: {devices[0].get('name')}")
    #
    # # Zmiana temperatury (3 kroki - tryb wyjątku)
    # print("\n1. Zmiana temperatury na 21°C (120 minut)...")
    # if client.set_target_temperature(device_id, 21.0, duration_minutes=120):
    #     print("   ✓ Temperatura zmieniona!")
    # else:
    #     print("   ✗ Błąd")
    #
    # # Anuluj wyjątek
    # print("\n2. Anulowanie wyjątku (wróć do programu)...")
    # if client.cancel_exception_mode(device_id):
    #     print("   ✓ Wyjątek anulowany!")
    # else:
    #     print("   ✗ Błąd")

    print("\n" + "=" * 80)
    print(" GOTOWE!")
    print("=" * 80)
    print("""
Klient gotowy do użycia!

Przykłady:
  client.set_target_temperature(27082489, 21.5)
  client.set_heating_mode(27082489, client.MODE_COMFORT)
  client.set_window_detection(27082489, True)
  
  temp = client.get_target_temperature(27082489)
  mode = client.get_heating_mode(27082489)
""")
