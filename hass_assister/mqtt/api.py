from typing import Dict, List
import asyncio
import signal
from loguru import logger
import time
from gmqtt import Client as MQTTClient
from gmqtt.mqtt.constants import MQTTv311


class MyMQTT(object):
    def __init__(self,
                 broker: str,
                 port: int = 1883,
                 keepalive: int = 60,
                 auth: List[str] = [None, None],
                 event_functions=None,
                 client_id: str = 'client_id',
                 event_loop=None) -> None:
        default_events = {'on_connect': self.on_connect,
                          'on_message': self.on_message,
                          'on_disconnect': self.on_disconnect,
                          'on_subscribe': self.on_subscribe}
        if event_functions is None:
            event_functions = {}

        self.event_functions = default_events
        self.event_functions.update(event_functions)

        self.client = MQTTClient(client_id)
        self.auth = auth
        self.broker = broker
        self.port = port
        self.keepalive = keepalive
        self.stop = asyncio.Event()

        if event_loop is None:
            loop = asyncio.get_event_loop()
        else:
            loop = event_loop

        loop.add_signal_handler(signal.SIGINT, self.ask_exit)
        loop.add_signal_handler(signal.SIGTERM, self.ask_exit)

        self.client = MQTTClient(client_id)

        for _ in [k for k, v in self.event_functions.items() if v is None]:
            logger.warning(f'mqtt no function assigned to {k}')
            self.event_functions.pop(k)

        for k, v in self.event_functions.items():
            setattr(self.client, k, v)

        if any(self.auth):
            self.client.set_auth_credentials(*self.auth)

        loop.create_task(self.start(self.broker))


    async def start(self, broker):
        logger.info('starting mqtt')
        try:
            await self.client.connect(broker, port=self.port, keepalive=self.keepalive, version=MQTTv311)
        except OSError as e:
            logger.error(f'unable to connect to mqtt with following error {e}')
        else:
            await self.stop.wait()
            await self.client.disconnect()

    def publish(self, topic, message, qos=1):
        self.client.publish(topic, message, qos=qos)

    def on_connect(self, client, flags, rc, properties):
        logger.info('MQTT Connected')
        client.subscribe('#')

    def on_message(self, client, topic, payload, qos, properties):
        logger.info(f'MQTT RECV MSG: {topic} {payload}')

    def on_disconnect(self, client, packet, exc=None):
        logger.info('MQTT Disconnected')

    def on_subscribe(self, client, mid, qos):
        logger.info('MQTT SUBSCRIBED')

    def ask_exit(self, *args):
        asyncio.Event().set()
