import magichue
from loguru import logger


async def get_all_lights(hass):
    return [i['entity_id'] async for i in hass if i['state'] in ('on', 'off') and 'light' in i['entity_id'].lower()]


async def control_lights(message, **kwargs):
    hass = kwargs.get('hass', None)
    if isinstance(message, bytes):
        message = message.decode()
    if message not in ('turn_on', 'turn_off'):
        logger.warning(f'supplied {message} but expected turn_on/off')
        return
    if not hass:
        logger.warning('there are no hass device list available, aborting')
        return
    devices = get_all_lights(hass)
    logger.debug(f'found following light {devices}')
    async for entity in devices:
        domain, *_ = entity.split('.')
        q = f'{hass.url.strip("/")}/api/services/{domain}/{message}'
        logger.debug(f'query {q}')
        try:
            async with aiohttp.ClientSession() as s, \
                    s.post(q, headers={'Authorization': f'Bearer {hass.auth_token}'}, json={'entity_id': entity}) as response:
                r = await response.json()
                logger.debug(f'response: {r}')
        except aiohttp.ClientConnectorError as e:
            logger.error(f'failed connecting to {q} with error {e}')
        except aiohttp.ContentTypeError as e:
            logger.error(f'invalid JSON from HASS {e}')
            logger.debug(f'{response}')


def check_light(host, **kwargs):
    light = magichue.Light(host)
    print(light.on)
    print(light.rgb)
    print(light.saturation)
    print(light.is_white)
    light.is_white = True
    light.on = True
    light.rgb = (100, 100, 100)
    # light.is_white = False
    # light.rgb = (100, 100, 100)
    # light.rgb(255, 0, 0)
    # light.brightness = 20
