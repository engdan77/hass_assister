import magichue
from loguru import logger
import aiohttp


async def aiter(iterable):
    for item in iterable:
        yield item


def get_all_lights(hass):
    lights = []
    for domain in ("switch", "light"):
        for device in hass.config.get(domain, []):
            if "devices" in device:
                for subdevice in device.get("devices", {}).values():
                    name = subdevice.get("name", "")
            else:
                name = device.get("name", "")
            if "light" in name or "lamp" in name:
                lights.append(f'{domain}.{name.replace(" ", "_").lower()}')
    logger.debug(f"found following lights {lights}")
    return lights


async def control_lights(message, **kwargs):
    hass = kwargs.get("hass", None)
    if isinstance(message, bytes):
        message = message.decode()
        cmd, *only_devices = message.rsplit('_', message.count('_') - 1)
    if cmd not in ("turn_on", "turn_off"):
        logger.warning(f"supplied {message} but expected turn_on/off")
        return
    if not hass:
        logger.warning("there are no hass device list available, aborting")
        return
    devices = get_all_lights(hass)
    logger.debug(f"found following light {devices}")
    async for entity in aiter(devices):
        if only_devices:
            if not any([_ in only_devices for _ in ('and', 'or')]):
                operator = 'and'
            else:
                operator = only_devices.pop(0)
            op = {'and': all, 'or': any}.get(operator, any)
            c = [True for d in only_devices if d in entity]
            if not op(c) or not c:
                logger.debug(f'skipping "{entity}" because limiting to {only_devices} with operator {op.__name__}')
                continue
        domain, *_ = entity.split(".")
        q = f'{hass.url.strip("/")}/api/services/{domain}/{cmd}'
        logger.debug(f"query {q}")
        try:
            async with aiohttp.ClientSession() as s, s.post(
                q,
                headers={"Authorization": f"Bearer {hass.auth_token}"},
                json={"entity_id": entity},
            ) as response:
                r = await response.json()
                logger.debug(f"response: {r}")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"failed connecting to {q} with error {e}")
        except aiohttp.ContentTypeError as e:
            logger.error(f"invalid JSON from HASS {e}")
            logger.debug(f"{response}")


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
