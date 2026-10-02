import json
import logging
import math
import threading
import paho.mqtt.client as mqtt
from Ports.sensor import sensor_measurement

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
        self._stop = threading.Event()
        self._online = threading.Event()

        # Klient MQTT
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_connect_fail = self._on_connect_fail
        self._client.on_message = self._on_message
        self._client.connect_timeout = 3.0
        self._client.reconnect_delay_set(min_delay=1, max_delay=60)

        # Uruchom MQTT w osobnym wątku żeby nie blokować GUI
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        delay = 1
        try:
            while not self._stop.is_set():
                try:
                    self._client.connect(self.BROKER_ADDRESS, self.BROKER_PORT, self.BROKER_KEEPALIVE)
                except OSError:
                    self._on_connect_fail(self._client, None)
                    if self._stop.wait(delay):
                        return
                    delay = min(delay * 2, 60)
                    continue
                # close() can race a blocking connect(). Do not enter the network
                # loop or start another connection after shutdown was requested.
                if self._stop.is_set():
                    self._client.disconnect()
                    return
                self._client.loop_forever()
                return
        finally:
            self._online.clear()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if self._stop.is_set():
            client.disconnect()
            return
        if reason_code != 0:
            self._online.clear()
            logger.warning("MQTT connection rejected for %s", self._name)
            return
        self._online.set()
        logger.info("MQTT connected for %s", self._name)
        client.subscribe(self._topic)

    def _on_connect_fail(self, client, userdata):
        self._online.clear()
        logger.warning("MQTT unavailable for %s; retrying with backoff", self._name)

    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        self._online.clear()
        if not self._stop.is_set():
            logger.warning("MQTT disconnected for %s; waiting to reconnect", self._name)

    def is_online(self) -> bool:
        return self._online.is_set()

    def close(self):
        """Stop retries and join the MQTT worker; call outside the UI thread."""
        self._stop.set()
        self._online.clear()
        self._client.disconnect()
        if self._thread.ident is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=5)
            if self._thread.is_alive():
                raise TimeoutError("MQTT worker did not stop")

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
        return sensor_measurement(self._data, key)
