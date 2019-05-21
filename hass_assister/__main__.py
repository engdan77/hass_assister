from .scheduler import MyScheduler
from fastapi import FastAPI
import uvicorn
import asyncio
from datetime import datetime
from loguru import logger
import easyconf
from appdirs import user_config_dir
from pathlib import Path
import functools
from .hass_common import HassInstance

default_config = {
    'hass_url': {'initial': 'https://localhost:8123', 'default': 'http://localhost:8123'},
    'hass_api_key': {'initial': '', 'default': ''},
    'hass_update_frequency_seconds': {'initial': 10, 'default': 10}
}

initial_scheduled_tasks = [
    ('hass_assister.tick', 'interval', {'seconds': 3, 'id': 'tick'}),
]

app = FastAPI()


@app.get('/')
async def read_root():
    return {'hello': 'world'}


async def tick():
    logger.info('Tick! The time is: %s' % datetime.now())


async def start_uvicorn():
    await uvicorn.run(app, host='0.0.0.0', port=8000)


async def get_hass_instance():
    pass


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
    conf = init_settings(default_config)

    # configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)

    # init scheduler
    scheduler = MyScheduler(initial_scheduled_tasks)
    logger.debug(f'scheduler started {scheduler}')

    # init hass-instance
    hass = HassInstance(conf['hass_url'], conf['hass_api_key'], scheduler=scheduler, update_freq=conf['hass_update_frequency_seconds'])

    # start event-loop
    asyncio.get_event_loop().run_until_complete(server.serve())


if __name__ == '__main__':
    main()
