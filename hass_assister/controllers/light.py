import magichue
from loguru import logger
import aiohttp
import asyncio
from collections import deque


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


async def all_lights(devices, hass=None, mode="turn_off"):
    async for entity in aiter(devices):
        await control_light(mode, entity, hass)


async def control_lights(message, max_count=100, **kwargs):
    hass = kwargs.get("hass", None)
    logger.debug(f"control lights with following states {hass.states}")
    devices = get_all_lights(hass)
    if isinstance(message, bytes):
        message = message.decode()
        cmd, *only_devices = message.rsplit("_", message.count("_") - 1)
    if cmd == "stop_cycle":
        logger.info("stopping light cycle")
        hass.states["cycle_light_enabled"] = False
    if cmd == "start_cycle":
        logger.info("starting light cycle")
        hass.states["blink_light_enabled"] = False
        hass.states["cycle_light_enabled"] = True
        # turn all off first
        await all_lights(devices, hass, "turn_off")
        current_count = 0
        rotate_list = deque(devices)
        while current_count <= max_count and hass.states["cycle_light_enabled"]:
            current_count += 1
            rotate_list.rotate(1)
            first, second, *_ = list(rotate_list)
            logger.debug(f"cycling lights on:{first}, off:{second}")
            await control_light("turn_on", first, hass)
            await control_light("turn_off", second, hass)
            await asyncio.sleep(1)
        logger.debug("stop cycle")
        hass.states["blinking_light_enabled"] = False
        await all_lights(devices, hass, "turn_off")
        logger.info("light cycle stopped")
    if cmd == "stop_blink":
        logger.info("stopping light blink")
        hass.states["blink_light_enabled"] = False
    if cmd == "start_blink":
        logger.info("starting light blink")
        hass.states["cycle_light_enabled"] = False
        hass.states["blink_light_enabled"] = True
        current_count = 0
        while current_count <= max_count and hass.states["blink_light_enabled"]:
            current_count += 1
            await asyncio.sleep(1)
            await all_lights(devices, hass, "turn_on")
            await asyncio.sleep(1)
            await all_lights(devices, hass, "turn_off")
        logger.debug("stop blink")
        hass.states["blink_light_enabled"] = False
        logger.info("light blink stopped")
    if cmd not in ("turn_on", "turn_off", "start_cycle", "blink_light"):
        logger.warning(
            f"supplied {message} but expected turn_on, turn_off, turn_on_device1, start/stop_cycle, start/stop_blink"
        )
        return
    if not hass:
        logger.warning("there are no hass device list available, aborting")
        return
    logger.debug(f"found following light {devices}")
    async for entity in aiter(devices):
        if only_devices:
            if not any([_ in only_devices for _ in ("and", "or")]):
                operator = "and"
            else:
                operator = only_devices.pop(0)
            op = {"and": all, "or": any}.get(operator, any)
            c = [True for d in only_devices if d in entity]
            if not op(c) or not c:
                logger.debug(
                    f'skipping "{entity}" because limiting to {only_devices} with operator {op.__name__}'
                )
                continue
        await control_light(cmd, entity, hass)


async def control_light(cmd, entity, hass):
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
