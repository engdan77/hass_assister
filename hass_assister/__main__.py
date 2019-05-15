from fastapi import FastAPI
import uvicorn
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
import easyconf
from appdirs import user_config_dir
from pathlib import Path

from hass_assister.hass_common.api import HassInstance

import time

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

async def start_scheduler(scheduler_):
    scheduler_.add_job(tick, 'interval', seconds=3, id='tick')
    scheduler_.start()

async def get_hass_instance():
    pass

def get_settings():
    p = globals().get('__package__')
    conf_path = Path(user_config_dir(p)) / Path(f'{p}.yaml')
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"creating {conf_path}")
    conf = easyconf.Config(str(conf_path))
    hass_host = conf.hass_host(initial='localhost', default='localhost')
    return conf


if __name__ == '__main__':
    config = get_settings()
    # Configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)
    loop = asyncio.get_event_loop()

    # scheduler.add_job()
    loop.create_task(start_scheduler(scheduler))
    loop.run_until_complete(server.serve())
