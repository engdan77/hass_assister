from hass_assister.mqtt.custom_handler import on_hass_mqtt_message
from hass_assister.settings.api import init_settings
from .scheduler import MyScheduler
from fastapi import FastAPI
import uvicorn
from datetime import datetime
from loguru import logger
from .hass_common import HassInstance
from .mqtt import MyMQTT
import asyncio


def def_conf(value):
    return {_: value for _ in ('initial', 'default')}

default_initial_scheduled_tasks = [
        ['hass_assister.ping', 'interval', {'seconds': 60, 'id': 'tick'}],
        ]

default_config = {
    'hass_url': {'initial': 'http://localhost:8123', 'default': 'http://localhost:8123'},
    'hass_api_key': def_conf(''),
    'hass_update_frequency_seconds': def_conf(10),
    'mqtt_broker': def_conf('localhost'),
    'mqtt_user': def_conf(''),
    'mqtt_password': def_conf(''),
    'initial_scheduled_tasks': {
        'initial': default_initial_scheduled_tasks,
        'default': default_initial_scheduled_tasks
    }
}

app = FastAPI()


@app.get('/')
async def read_root():
    return {'hello': 'world'}


async def ping():
    logger.debug('Pong! The time is: %s' % datetime.now())


async def start_uvicorn():
    await uvicorn.run(app, host='0.0.0.0', port=8000)


def main():
    # configuration
    c = init_settings(default_config)

    # configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)

    # event loop
    loop = asyncio.get_event_loop()

    # init scheduler
    initial_scheduled_tasks = c['initial_scheduled_tasks']
    scheduler = MyScheduler(initial_scheduled_tasks)
    logger.debug(f'scheduler started {scheduler}')

    # init hass-instance
    global hass
    hass = HassInstance(c['hass_url'], c['hass_api_key'], scheduler=scheduler, update_freq=c['hass_update_frequency_seconds'])

    # init mqtt
    mqtt_events = {'on_message': on_hass_mqtt_message}
    mqtt = MyMQTT(c['mqtt_broker'], auth=(c['mqtt_user'], c['mqtt_password']), event_functions=mqtt_events, hass_ref=hass)

    # start event-loop
    loop.run_until_complete(server.serve())
    logger.info('stopping hass_assister')

if __name__ == '__main__':
    main()
