from typing import Union, Dict
import aiohttp
from hass_assister.scheduler import MyScheduler
from loguru import logger
from nested_lookup import nested_lookup
import fs
import yaml
from urllib.parse import urlparse

class HassInstance(object):
    def __init__(self, url: str,
                 auth_token: str,
                 scheduler: Union[MyScheduler, None] = None,
                 share: str = 'homeassistant',
                 update_freq: int = 10):
        self.url = url
        self.auth_token = auth_token
        self.scheduler = scheduler
        self.update_freq = update_freq
        self.attributes = None
        self.share = share
        self.config = None

        logger.debug('initializing HassInstance object')
        if scheduler:
            scheduler.add_task(self.update_sensor_status, 'interval', seconds=self.update_freq)

        logger.debug('fetching Home Assistant configuration')
        self.update_configuration()

    async def update_sensor_status(self):
        q = f'{self.url.strip("/")}/api/states'
        logger.debug(f'query {q}')
        try:
            async with aiohttp.ClientSession() as s, \
                    s.get(q, headers={'Authorization': f'Bearer {self.auth_token}'}) as response:
                self.attributes = await response.json()
                entity_count = len(nested_lookup('entity_id', self.attributes))
                logger.debug(f'{entity_count} entities pulled')
        except aiohttp.ClientConnectorError as e:
            logger.error(f'failed connecting to {q} with error {e}')
        except aiohttp.ContentTypeError as e:
            logger.error(f'invalid JSON from HASS {e}')
            logger.debug(f'{response}')


    def update_configuration(self):
        host = urlparse(self.url).netloc.split(':')[0]
        try:
            f = fs.open_fs(f'smb://{host}/{self.share}').open('configuration.yaml').read().replace('!', '')
        except fs.errors.CreateFailed:
            logger.error('unable to connect to HASS using smb, please verify hostname')
        else:
            self.config = yaml.load(f)

    def get_entity_info(self, mqtt_topic: str) -> Dict:
        c = self.config
        config_lists = [c[root_key] for root_key in c.keys() if type(c[root_key]) is list]
        valid_entities = [_dict
                            for _list in config_lists
                            for _dict in _list
                            if 'platform' in _dict and _dict['platform'] == 'mqtt']
        return next(iter([e for e in valid_entities if e['state_topic'] == mqtt_topic]), None)


