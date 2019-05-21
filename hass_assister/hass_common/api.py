from typing import Union
import aiohttp
from hass_assister.scheduler import MyScheduler
from loguru import logger
from nested_lookup import nested_lookup

class HassInstance(object):
    def __init__(self, url: str, auth_token: str, scheduler: Union[MyScheduler, None] = None, update_freq: int = 10):
        self.url = url
        self.auth_token = auth_token
        self.scheduler = scheduler
        self.update_freq = update_freq
        self.attributes = None

        logger.debug('initializing HassInstance object')
        if scheduler:
            scheduler.add_task(self.update_sensor_status, 'interval', seconds=self.update_freq)

    async def update_sensor_status(self):
        q = f'{self.url.strip("/")}/api/states'
        logger.debug(f'query {q}')
        async with aiohttp.ClientSession() as s, s.get(q, headers={'Authorization': f'Bearer {self.auth_token}'}) as response:
            self.attributes = await response.json()
            entity_count = len(nested_lookup('entity_id', self.attributes))
            logger.debug(f'{entity_count} entities pulled')
