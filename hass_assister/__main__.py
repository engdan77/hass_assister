from hass_assister.mqtt.custom_handler import on_hass_mqtt_message
from hass_assister.settings.api import init_settings
from .scheduler import MyScheduler
from fastapi import FastAPI
import uvicorn
from datetime import datetime
from loguru import logger
from .hass_common import HassInstance
from .mqtt import MyMQTT
import asyncio
import sys
from pprint import pprint as pp


default_initial_scheduled_tasks = [
    ["hass_assister.ping", "interval", {"seconds": 60, "id": "tick"}],
]
ip_device = {"enabled": False, "address": "127.0.0.1", "port": 9999}
default_config = {
    "hass_url": {"initial": "http://localhost:8123"},
    "hass_api_key": {"initial": ""},
    "hass_update_frequency_seconds": {"initial": 60},
    "mqtt_broker": {"initial": "localhost"},
    "mqtt_user": {"initial": ""},
    "mqtt_password": {"initial": ""},
    "initial_scheduled_tasks": {"initial": default_initial_scheduled_tasks},
    "philips_ip": {"initial": ""},
    "philips_user": {"initial": ""},
    "philips_password": {"initial": ""},
    "philips_mac": {"initial": ""},
    "dummy_display": {"initial": ip_device.copy()},
    "kodi_display": {"initial": ip_device.copy()},
    "mqtt_functions": {
        "initial": {
            "tv_start_media": "hass_assister.controllers.tv.start_media",
            "tv_start_channel": "hass_assister.controllers.tv.start_channel",
            "tv_command": "hass_assister.controllers.tv.command",
            "lights_control": "hass_assister.controllers.light.control_lights",
        }
    },
    "mqtt_replacement": {
        "initial": {
            ("from/topic_(..)", "from_message"): ("/to_topic_\\1", "to_message"),
            ("solna_hall_light/state", "on"): ("cmnd/solnarf/Backlog", "rfraw AAB04E050801540A0000BE04BA279201020302030302020303020302030202030203030202030302030203020203030202030302020303020203020303020203030202030203030202030203020303020455 ; rfraw 177"),
            ("solna_hall_light/state", "off"): ("cmnd/solnarf/Backlog", "rfraw AAB04E0508015409F600BE04B0272E01020302030302020303020302030202030203030202030302030203020203030202030302020303020203020303020203030202030203020302030203020303020455 ; rfraw 177"),
            ("tele/solnarf/RESULT", ".*?AA B0 4E 0508 0154 0A0000BE04BA2792010203020303020203030203020302020302030302020303020302030202030302020303020203030202030203030202030302020302030302020302030203030204 55.*"): ("solna_hall_light/state", "on"),
            ("tele/solnarf/RESULT", ".*?AA B0 4E 0508 0154 09F6 00BE04B0272E010203020303020203030203020302020302030302020303020302030202030302020303020203030202030203030202030302020302030203020302030203030204 55.*"): ("solna_hall_light/state", "off")
        }
    },
}

states = {'cycle_light_enabled': False,
          'blink_light_enabled': False}

app = FastAPI()


@app.get("/")
async def read_root():
    return {"hello": "world"}


async def ping():
    logger.debug("Pong! The time is: %s" % datetime.now())


async def start_uvicorn():
    await uvicorn.run(app, host="0.0.0.0", port=8000)


def main():
    # add better logging
    logger.remove()
    logger.add(sys.stdout, backtrace=True, diagnose=True, enqueue=True)

    # configuration
    c = init_settings(default_config)
    logger.debug(f"using following configuration:\n{c}")

    # configure uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)

    # event loop
    loop = asyncio.get_event_loop()

    # init scheduler
    initial_scheduled_tasks = c["initial_scheduled_tasks"]
    scheduler = MyScheduler(initial_scheduled_tasks)
    logger.debug(f"scheduler started {scheduler}")

    # init hass-instance
    global hass
    hass = HassInstance(
        c["hass_url"],
        c["hass_api_key"],
        scheduler=scheduler,
        update_freq=c["hass_update_frequency_seconds"],
        states=states
    )

    # init mqtt
    mqtt_events = {"on_message": on_hass_mqtt_message}
    mqtt = MyMQTT(
        c["mqtt_broker"],
        auth=(c["mqtt_user"], c["mqtt_password"]),
        event_functions=mqtt_events,
        hass_ref=hass,
        app_config=c,
    )

    # start event-loop
    loop.run_until_complete(server.serve())
    logger.info("stopping hass_assister")


if __name__ == "__main__":
    main()
