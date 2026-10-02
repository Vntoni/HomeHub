import json
import logging
import math
import threading
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


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
                data = json.loads(msg.payload)
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
                for key in ("temperature", "humidity", "battery", "linkquality"):
                    if key not in data:
                        continue
                    value = data[key]
                    if isinstance(value, bool) or not math.isfinite(float(value)):
                        raise ValueError("Expected a finite measurement")
                    if key == "linkquality":
                        int(value)  # Match the public getter's accepted values.
            except (ValueError, TypeError, OverflowError):
                logger.warning("Invalid MQTT measurement for %s", self._name)
                return

            # Publish only after validating all fields; retain the last valid cache
            # if decoding or conversion failed. Partial payload semantics stay intact.
            self._data = data
            if self._on_update:
                try:
                    self._on_update(self._name, data)
                except Exception as exc:
                    logger.error("Sensor callback failed for %s (%s)",
                                 self._name, type(exc).__name__)

    # --- SensorPort interface ---

    def get_data(self) -> dict:
        """Zwraca ostatnie dane z czujnika"""
        return self._data

    def get_temperature(self) -> float:
        """Zwraca ostatnią temperaturę w °C"""
        return float(self._data.get("temperature", 0.0))

    def get_humidity(self) -> float:
        """Zwraca ostatnią wilgotność w %"""
        return float(self._data.get("humidity", 0.0))

    def get_battery_level(self) -> float:
        """Zwraca poziom baterii w %"""
        return float(self._data.get("battery", 0.0))

    def get_link_quality(self) -> int:
        """Zwraca jakość sygnału Zigbee (lqi)"""
        return int(self._data.get("linkquality", 0))
