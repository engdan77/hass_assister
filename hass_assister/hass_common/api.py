from typing import Union
import aiohttp
from hass_assister.scheduler import MyScheduler
from loguru import logger

class HassInstance(object):
    def __init__(self, url: str, auth_token: str, scheduler: Union[MyScheduler, None] = None, update_freq: int = 10):
        self.url = url
        self.auth_token = auth_token
        self.scheduler = scheduler
        self.update_freq = update_freq
        self.sensors = None

        logger.debug('initializing HassInstance object')
        if scheduler:
            scheduler.add_task(self.update_sensor_status, 'interval', seconds=self.update_freq)

    async def update_sensor_status(self):
        logger.info(f'query {self.url}')
        async with aiohttp.ClientSession() as s, s.get(self.url, headers={'Authorization': f'Bearer {self.auth_token}'}) as response:
            r = await response.read()
            logger.info(r)
