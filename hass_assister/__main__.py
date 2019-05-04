from fastapi import FastAPI
import uvicorn
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger
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

if __name__ == '__main__':

    # Configure uvicorn
    config = uvicorn.Config(app, host='0.0.0.0', port=8000)
    server = uvicorn.Server(config)
    loop = asyncio.get_event_loop()

    loop.create_task(start_scheduler(scheduler))
    loop.run_until_complete(server.serve())
