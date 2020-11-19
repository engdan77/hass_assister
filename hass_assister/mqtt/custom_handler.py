from loguru import logger
import subprocess
import json
import asyncio
import urllib3
import requests
import datetime
from hass_assister.helper import import_item
import re

# This could be customised for replacing specific words before displaying those
REPLACE_TEXT = {
    ("light", "coffee"): {r"\b1\b": "ON", r"\b0\b": "OFF"},
    ("rf bridge",): {
        r"\b.{12}D549EE\b": "Motion Kitchen",
        r"\b.{12}D5842E\b": "Motion Livingroom",
        r"\b.{12}D5641E\b": "Motion Laundryroom",
        r"\b.{12}D35FFF\b": "Door bell",
        r"\b.{12}FD9921\b": "Entrance door",
        r"\b.{12}D44FAE\b": "Entrance motion",
        r"\b.{12}2E7EE1\b": "Laundryoom door",
    },
}

EXCLUDE_TEXT = ("RF Bridge 0", "rf bridge Motion Livingroom")


def replace_mqtt_message(
    from_topic,
    to_topic=None,
    input_topic=None,
    from_message=None,
    to_message=None,
    input_message=None,
):
    if not re.match(from_topic, input_topic, re.IGNORECASE):
        return None
    output_topic = re.sub(from_topic, to_topic, input_topic, re.IGNORECASE)
    if to_message:
        output_message = re.sub(
            from_message, to_message, input_message.decode(), re.IGNORECASE
        )
    else:
        output_message = input_message
    if not from_topic == to_topic or not from_message == to_message:
        return output_topic, output_message


async def tcp_send(address, port, data, loop=None):
    reader, writer = await asyncio.open_connection(address, port, loop=loop)
    logger.debug(f"sending {data}")
    writer.write(data.encode())
    data = await reader.read(100)
    logger.debug(f"received: {data.decode()}")
    logger.debug("close the socket")
    writer.close()


def tcp_send_blocking(address, port, data):
    d = data.replace('"', '\\"')
    command = f'echo "{d}" | nc {address} {port}'
    logger.debug(command)
    try:
        r = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError:
        logger.warning(f"failed connecting to dummy_display {address}:{port}")
    else:
        logger.debug(r)


def adjust_text(input_payload):
    output_payload = input_payload.replace("\\\n", " ").lower()
    input_payload = input_payload.replace("\\\n", " ").lower()
    for match_words, rules in REPLACE_TEXT.items():
        if any((x.lower() in input_payload for x in match_words)):
            for match, word in rules.items():
                output_payload = re.sub(
                    match.lower(), word, output_payload, re.IGNORECASE
                )
    logger.debug(f'replacing "{input_payload}"" with "{output_payload}"')
    return output_payload


def adjust_display_text(data, adapt_for="dummy_display"):
    e, m = data
    if adapt_for == "dummy_display":
        e = e.replace(" ", "\\\n")
        display_text = adjust_text(f"{e}\\\n{m}")
    elif adapt_for == "kodi_display":
        display_text = adjust_text(f"{e} {m}")
    else:
        return None, None, None
    if any([_.lower() in display_text.lower() for _ in EXCLUDE_TEXT]):
        logger.debug(f"discarding message {display_text}")
        return None, None, None
    return e, m, display_text


async def send_dummy_display(address, port, data, display_type="text", loop=None):
    """This is a function for sending sensor updates to dummy display

    :param address:
    :param port:
    :param data:
    :param display_type:
    :param loop:
    """
    display_types = ("text", "image")
    if display_type not in display_types:
        raise ValueError("display_type has to be text or image")
    if display_type == "text":
        e, m, display_text = adjust_display_text(data, adapt_for="dummy_display")
        payload = {"text": {"input_text": display_text}}
        p = json.dumps(payload)
        if not any((x in e for x in ("Bridge",))):
            logger.debug(f"sending message to dummy display {display_text}")
            tcp_send_blocking(address, port, p)


def send_kodi_message(address, port, data):
    """This function is used to forward MQTT events to Kodi as notification

    :param address:
    :param port:
    :param data:
    """
    from kodijson import Kodi

    e, m, display_text = adjust_display_text(data, adapt_for="kodi_display")
    kodi = Kodi(f"http://{address}:{port}/jsonrpc")
    try:
        logger.debug(f"sending message to Kodi {display_text}")
        time = datetime.datetime.now().strftime("%H:%M")
        kodi.JSONRPC.Ping()
        kodi.GUI.ShowNotification({"title": time, "message": display_text})
    except (
        ConnectionError,
        ConnectionRefusedError,
        requests.exceptions.ConnectionError,
        urllib3.exceptions.NewConnectionError,
        urllib3.exceptions.MaxRetryError,
    ):
        logger.warning(f"Unable to conned to Kodi {address}:{port}")
    except Exception:
        logger.exception("Something unexpected went wrong while sending to Kodi")


def process_mqtt_timers(mqtt_timer_counters, mqtt_client):
    for timer_id, counter in mqtt_timer_counters.copy().items():
        counter -= 1
        mqtt_timer_counters[timer_id] = counter
        if counter <= 0:
            mqtt_timer_counters.pop(timer_id)
            mqtt_timer_setting = mqtt_client.properties["app_config"].get(
                "mqtt_timer", {}
            )
            (
                on_topic,
                on_message,
                timer_secs,
                new_topic,
                new_message,
            ) = mqtt_timer_setting[timer_id]
            logger.debug(
                f"timer for {timer_id} expired, sending {new_topic} with {new_message}"
            )
            mqtt_client.publish(new_topic, new_message)


async def on_hass_mqtt_message(client, topic, payload, qos, properties):
    """Main callback used for mqtt messages

    :param client:
    :param topic:
    :param payload:
    :param qos:
    :param properties:
    """
    logger.debug(
        f"Incoming MQTT topic:{topic}, payload:{payload}, qos:{qos}, properties:{properties}"
    )
    hass = client.properties.get("hass_ref")
    app_config = client.properties.get("app_config")
    loop = client._connected._loop
    # hass.attributes = states of entities (entity_id, state)
    if hass:
        entity = hass.get_entity_info(topic)
    else:
        entity = {"name": None}
    if entity:
        e, m = (entity["name"], payload.decode())
        logger.info(f"Processing MQTT message: {e} changed to {m}")
        dummy_display_settings = client.properties["app_config"]["dummy_display"]
        if dummy_display_settings["enabled"]:
            address = dummy_display_settings["address"]
            port = dummy_display_settings["port"]
            await send_dummy_display(
                address, port, (e, m), display_type="text", loop=client._connected._loop
            )
        kodi_display_settings = client.properties["app_config"]["kodi_display"]
        if kodi_display_settings["enabled"]:
            address = kodi_display_settings["address"]
            port = kodi_display_settings["port"]
            blocking_call = loop.run_in_executor(
                None, send_kodi_message, address, port, (e, m)
            )
            completed, pending = await asyncio.wait([blocking_call])

    # run function if one is found in mqtt message
    *_, t = topic.split("/")
    mqtt_functions = client.properties["app_config"].get("mqtt_functions", {})
    if t in mqtt_functions.keys():
        logger.info(
            f"found {t} in mqtt topic and will run {mqtt_functions[t]}({payload})"
        )
        f = import_item(mqtt_functions[t])
        logger.debug(f"awaiting {f}")
        await f(payload, hass=hass, app_config=app_config)

    # if MQTT replace is found
    mqtt_replacement_setting = client.properties["app_config"].get(
        "mqtt_replacement", {}
    )
    for (
        (from_topic, from_message),
        (to_topic, to_message),
    ) in mqtt_replacement_setting.items():
        if re.match(from_topic, topic, re.IGNORECASE) and re.match(
            from_message, payload.decode(), re.IGNORECASE
        ):
            new_topic, new_payload = replace_mqtt_message(
                from_topic, to_topic, topic, from_message, to_message, payload
            )
            # logger.debug(from_topic, from_message, to_topic, to_message)
            logger.debug(f"sending {new_topic} with {new_payload}")
            client.publish(new_topic, new_payload)

    # if MQTT timer is found
    mqtt_timer_setting = client.properties["app_config"].get("mqtt_timer", {})
    mqtt_timer_counters = client.properties["mqtt_timer_counters"]
    for timer_id, (
        on_topic,
        on_message,
        timer_secs,
        new_topic,
        new_message,
    ) in mqtt_timer_setting.items():
        if re.match(on_topic, topic, re.IGNORECASE) and re.match(
            on_message, payload.decode(), re.IGNORECASE
        ):
            mqtt_timer_counters.update({timer_id: timer_secs})
