from typing import Union, Optional
from fastapi import FastAPI
import uvicorn
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
import easyconf
from appdirs import user_config_dir
from pathlib import Path
import functools


default_config = {
    'hass_host': {'initial': 'localhost', 'default': 'localhost'},
}


from hass_assister.hass_common.api import HassInstance

app = FastAPI()
scheduler = AsyncIOScheduler()

@app.get('/')
async def read_root():
    return {'hello': 'world'}


async def tick():
    logger.info('Tick! The time is: %s' % datetime.now())


async def start_uvicorn():
    loop = asyncio.get_event_loop()
    await uvicorn.run(app, host='0.0.0.0', port=8000)


class MyScheduler(object):
    def __init__(self, scheduler: AsyncIOScheduler, schedule_queue: Optional[asyncio.Queue]) -> None:
        pass


async def start_scheduler(scheduler_):
    scheduler_.add_job(tick, 'interval', seconds=3, id='tick')
    scheduler_.start()


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


if __name__ == '__main__':
    conf = init_settings(default_config)
    # Configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)

    asyncio.ensure_future(start_scheduler(scheduler))
    asyncio.get_event_loop().run_until_complete(server.serve())

