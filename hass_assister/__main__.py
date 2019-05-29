from .scheduler import MyScheduler
from fastapi import FastAPI
import uvicorn
from datetime import datetime
from loguru import logger
import easyconf
from appdirs import user_config_dir
from pathlib import Path
import functools
from .hass_common import HassInstance
from .mqtt import MyMQTT
import asyncio

def def_conf(value):
    return {_: value for _ in ('initial', 'default')}

default_config = {
    'hass_url': {'initial': 'https://localhost:8123', 'default': 'http://localhost:8123'},
    'hass_api_key': def_conf(''),
    'hass_update_frequency_seconds': def_conf(10),
    'mqtt_broker': def_conf('localhost'),
    'mqtt_user': def_conf(''),
    'mqtt_password': def_conf('')
}

initial_scheduled_tasks = [
    ('hass_assister.ping', 'interval', {'seconds': 60, 'id': 'tick'}),
]

app = FastAPI()

@app.get('/')
async def read_root():
    return {'hello': 'world'}


async def ping():
    logger.debug('Pong! The time is: %s' % datetime.now())


def on_hass_mqtt_message(client, topic, payload, qos, properties):
    logger.info(f'Processing MQTT message: {topic} {payload}')


async def start_uvicorn():
    await uvicorn.run(app, host='0.0.0.0', port=8000)


def init_settings(_default_config_params):
    p = globals().get('__package__')
    conf_path = Path(user_config_dir(p)) / Path(f'{p}.yaml')
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"creating {conf_path}")
    conf_obj = easyconf.Config(str(conf_path))
    conf = {}
    for param, initials in _default_config_params.items():
        conf[param] = functools.partial(getattr(conf_obj, param), **initials)()
    logger.info(f'configuration loaded {conf}')
    return conf

def main():
    # configuration
    c = init_settings(default_config)

    # configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)

    # event loop
    loop = asyncio.get_event_loop()

    # init mqtt
    mqtt_events = {'on_message': on_hass_mqtt_message}
    mqtt = MyMQTT(c['mqtt_broker'], auth=(c['mqtt_user'], c['mqtt_password']), event_functions=mqtt_events)

    # init scheduler
    scheduler = MyScheduler(initial_scheduled_tasks)
    logger.debug(f'scheduler started {scheduler}')

    # init hass-instance
    hass = HassInstance(c['hass_url'], c['hass_api_key'], scheduler=scheduler, update_freq=c['hass_update_frequency_seconds'])

    # start event-loop
    loop.run_until_complete(server.serve())
    logger.info('stopping hass_assister')

if __name__ == '__main__':
    main()
