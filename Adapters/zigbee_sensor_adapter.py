import json
import math
import threading
import paho.mqtt.client as mqtt


class ZigbeeSensorAdapter:
    """
    Adapter dla czujnika Zigbee (np. SONOFF SNZB-02P) przez Zigbee2MQTT/MQTT.
    Łączy się z brokerem MQTT w osobnym wątku i trzyma ostatnie dane w pamięci.
    Implementuje SensorPort.
    """

    BROKER_ADDRESS = "localhost"
    BROKER_PORT = 1883
    BROKER_KEEPALIVE = 60

    def __init__(self, sensor_name: str, on_update=None):
        """
        Args:
            sensor_name: Friendly name czujnika w Zigbee2MQTT, np. "Salon"
            on_update: opcjonalny callback(name, data) wywoływany przy każdej nowej wiadomości
        """
        self._name = f"czujnik_{sensor_name}"
        self._topic = f"zigbee2mqtt/{self._name}"
        self._data: dict = {}
        self._on_update = on_update

        # Klient MQTT
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        # Uruchom MQTT w osobnym wątku żeby nie blokować GUI
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self._client.connect(self.BROKER_ADDRESS, self.BROKER_PORT, self.BROKER_KEEPALIVE)
        self._client.loop_forever()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"[ZigbeeSensor:{self._name}] Connected, subscribing to {self._topic}")
        client.subscribe(self._topic)

    def _on_message(self, client, userdata, msg):
        if msg.topic == self._topic:
            try:
                self._data = json.loads(msg.payload)
                if self._on_update:
                    self._on_update(self._name, self._data)
            except json.JSONDecodeError:
                print(f"[ZigbeeSensor:{self._name}] Invalid JSON payload")

    # --- SensorPort interface ---

    def get_data(self) -> dict:
        """Zwraca ostatnie dane z czujnika"""
        return self._data

    def get_temperature(self) -> float | None:
        """Zwraca ostatnią temperaturę w °C"""
        return self._measurement("temperature")

    def get_humidity(self) -> float | None:
        """Zwraca ostatnią wilgotność w %"""
        return self._measurement("humidity")

    def get_battery_level(self) -> float | None:
        """Zwraca poziom baterii w %"""
        return self._measurement("battery")

    def get_link_quality(self) -> int | None:
        """Zwraca jakość sygnału Zigbee (lqi)"""
        value = self._measurement("linkquality")
        return int(value) if value is not None else None

    def _measurement(self, key: str) -> float | None:
        """Return None for an absent/invalid measurement; zero is valid."""
        if key not in self._data or self._data[key] is None:
            return None
        try:
            value = float(self._data[key])
        except (TypeError, ValueError, OverflowError):
            return None
        return value if math.isfinite(value) else None
