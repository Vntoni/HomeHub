import paho.mqtt.client as mqtt



class MQTTClient:

    CLIENT= "zigbee2mqtt/#"
    CLIENT_ADDRESS = "localhost"
    CLIENT_PORT = 1883
    CLIENT_KEEPALIVE = 60

    def __init__(self):
        self._filter_name = None
        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"Connected with result code {reason_code}")
        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe(self.CLIENT)

    def on_message(self, client, userdata, msg):
        expected_topic = f"zigbee2mqtt/{self._filter_name}"
        if msg.topic == expected_topic:
            import json
            data = json.loads(msg.payload)
            print(f"[{self._filter_name}] temp={data.get('temperature')} hum={data.get('humidity')} bat={data.get('battery')}")

    def get_data(self, name):
        self._filter_name = name
        self.mqttc.connect(self.CLIENT_ADDRESS, self.CLIENT_PORT, self.CLIENT_KEEPALIVE)
        self.mqttc.loop_forever()


if __name__ == "__main__":
    client = MQTTClient()
    client.get_data("Salon")  # podaj nazwę czujnika z Zigbee2MQTT
