from typing import Union, Optional, List, Dict, Any
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
initial_scheduled_tasks = [
    ['tick', 'interval', {'seconds': 3, 'id': 'tick'}],
]


from hass_assister.hass_common.api import HassInstance

app = FastAPI()


@app.get('/')
async def read_root():
    return {'hello': 'world'}


async def tick():
    logger.info('Tick! The time is: %s' % datetime.now())


async def start_uvicorn():
    loop = asyncio.get_event_loop()
    await uvicorn.run(app, host='0.0.0.0', port=8000)


class MyScheduler(object):
    def __init__(self,
                 initials: List[List],
                 schedule_queue: Optional[asyncio.Queue]=None) -> None:
        self.scheduler = AsyncIOScheduler()

        if scheduler_queue:
            self.queue = schedule_queue
        else:
            self.queue = asyncio.Queue()

        self.add_initials(initials)
        self.scheduler.start()

    def add_task(self, _func, _type, **kwargs):
        self.scheduler.add_job(globals()[_func], _type, **kwargs)

    def add_initials(self, initials):
        for _func, _type, kwargs in initials:
            self.add_task(_func, _type, **kwargs)


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
    # configuration
    conf = init_settings(default_config)

    # Configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)

    # scheduler
    scheduler_queue = asyncio.Queue()
    # scheduler = MyScheduler(scheduler_queue, initial_scheduled_tasks)
    scheduler = MyScheduler(initial_scheduled_tasks)

    # asyncio.ensure_future(start_scheduler(scheduler))
    asyncio.get_event_loop().run_until_complete(server.serve())

