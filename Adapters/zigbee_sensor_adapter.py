import json
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
        self._name = sensor_name
        self._topic = f"zigbee2mqtt/{sensor_name}"
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

