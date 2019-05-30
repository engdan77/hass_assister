from typing import Union, Dict
import aiohttp
from hass_assister.scheduler import MyScheduler
from loguru import logger
from nested_lookup import nested_lookup
import fs
import yaml

class HassInstance(object):
    def __init__(self, url: str, auth_token: str, scheduler: Union[MyScheduler, None] = None, host: str, share: str = 'homeassistant', update_freq: int = 10):
        self.url = url
        self.auth_token = auth_token
        self.scheduler = scheduler
        self.update_freq = update_freq
        self.attributes = None
        self.config = self.update_configuration(host, share)

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

    def update_configuration(self, host, share):
        f = fs.open_fs(f'smb://{host}/{share}').open('configuration.yaml').replace('!', '')
        self.config = yaml.load(f)

    def get_entity_info(self, mqtt_topic: str) -> Dict:
        c = self.config
        config_lists = [c[root_key] for root_key in c.keys() if type(c[root_key]) is list]
        valid_entities = [_dict
                            for _list in config_lists
                            for _dict in _list
                            if 'platform' in _dict and _dict['platform'] == 'mqtt']
        return next([e for e in valid_entities if e['state_topic'] == mqtt_topic], None)


