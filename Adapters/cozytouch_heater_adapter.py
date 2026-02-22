from Ports.heater import HeaterPort
from atlantic_client import AtlanticCozytouchClient

class CozyTouchHeaterAdapter(HeaterPort):
    """
    Adapter dla grzejnika Atlantic Cozy Touch
    Używa AtlanticCozytouchClient (znaleziony endpoint przez sniffing)
    """

    def __init__(self, client: AtlanticCozytouchClient, device_id: int):
        """
        Args:
            client: Instancja AtlanticCozytouchClient (współdzielona)
            device_id: ID urządzenia (np. 27082507)
        """
        self._client = client
        self._device_id = device_id

    async def refresh(self) -> None:
        """Odśwież stan grzejnika"""
        # Client odświeża wszystkie urządzenia naraz
        self._client.get_devices()

    async def set_power(self, on: bool) -> None:
        """
        Włącz/wyłącz grzejnik

        W trybie program używa się wyjątku z minimalną/maksymalną temperaturą
        """
        if on:
            # Włącz - ustaw normalną temperaturę (np. 20°C)
            self._client.set_target_temperature(self._device_id, 20.0, duration_minutes=120)
        else:
            # Wyłącz - ustaw minimalną temperaturę (7°C) lub anuluj wyjątek
            self._client.cancel_exception_mode(self._device_id)

    def get_power(self) -> bool:
        """
        Pobierz status zasilania

        Uznajemy że grzejnik jest "włączony" jeśli ma aktywny wyjątek (cap 157 = 1)
        """
        exception_mode = self._client.get_device_capability(self._device_id, 157)
        return exception_mode == "1" if exception_mode else False

    async def set_target_temperature(self, temp_c: float, duration_minutes: int = 120) -> None:
        """
        Ustaw temperaturę docelową

        W trybie PROGRAM używa trybu wyjątku (3 kroki):
        1. Czas trwania (cap 158)
        2. Aktywacja (cap 157)
        3. Temperatura (cap 40)

        Args:
            temp_c: Temperatura w °C (7-28)
            duration_minutes: Czas trwania wyjątku (domyślnie 120 min = 2h)
        """
        self._client.set_target_temperature(self._device_id, temp_c, duration_minutes)

    def get_target_temperature(self) -> float:
        """
        Pobierz temperaturę docelową

        Jeśli jest aktywny wyjątek (cap 157 = 1), zwraca cap 40 (temp wyjątku)
        W przeciwnym razie zwraca cap 17 (normalna target temp)
        """
        # Sprawdź czy jest aktywny wyjątek
        exception_active = self._client.get_device_capability(self._device_id, 157)

        if exception_active == "1":
            # Wyjątek aktywny - zwróć temperaturę wyjątku (cap 40)
            temp = self._client.get_device_capability(self._device_id, 40)
        else:
            # Normalny tryb - zwróć target temp (cap 17)
            temp = self._client.get_device_capability(self._device_id, 17)

        return float(temp) if temp else 0.0

    def get_current_temperature(self) -> float:
        """Pobierz aktualną temperaturę (capability 117)"""
        temp = self._client.get_actual_temperature(self._device_id)
        return float(temp) if temp else 0.0

    async def set_mode(self, mode: str) -> None:
        """
        Ustaw tryb pracy

        Możliwe tryby:
        - "manual" - tryb ręczny (capability 184 = 0)
        - "program" - tryb programowalny (capability 184 = 1)
        """
        if mode.lower() == "manual":
            self._client.set_mode_manual(self._device_id)
        elif mode.lower() == "program":
            self._client.set_mode_program(self._device_id)
        else:
            raise ValueError(f"Unknown mode: {mode}. Use 'manual' or 'program'")

    def get_mode(self) -> str:
        """
        Pobierz aktualny tryb pracy

        Returns:
            "manual" lub "program"
        """
        mode = self._client.get_device_capability(self._device_id, 184)
        if mode == "0":
            return "manual"
        elif mode == "1":
            return "program"
        return "unknown"

    def is_online(self) -> bool:
        """
        Sprawdź czy grzejnik jest online

        Uznajemy że grzejnik jest online jeśli:
        1. Istnieje w liście urządzeń
        2. Ma capabilities (dane)
        3. Temperatura aktualna nie jest None/0
        """
        try:
            # Sprawdź czy urządzenie istnieje
            for device in self._client.devices:
                if device.get('deviceId') == self._device_id:
                    # Jeśli ma capabilities, uznajemy że jest online
                    capabilities = device.get('capabilities', [])
                    if len(capabilities) > 0:
                        # Dodatkowo sprawdź czy ma aktualną temperaturę
                        temp = self.get_current_temperature()
                        # Jeśli temperatura > 0, na pewno jest online
                        if temp > 0:
                            return True
                        # Nawet jeśli temp = 0, ale ma capabilities, prawdopodobnie online
                        return True
                    return False
            return False
        except:
            # W razie błędu, uznajemy że offline
            return False

