from loguru import logger
import subprocess
import json
import re
import asyncio
import urllib3
import requests
import datetime
from hass_assister.helper import import_item
from functools import partial

REPLACE_TEXT = {('light', 'coffee'): {r'\b1\b': 'ON',
                                      r'\b0\b': 'OFF'},
                ('rf bridge',): {r'\b.{12}D549EE\b': 'Motion Kitchen',
                                 r'\b.{12}D5842E\b': 'Motion Livingroom',
                                 r'\b.{12}D5641E\b': 'Motion Laundryroom',
                                 r'\b.{12}D35FFF\b': 'Door bell',
                                 r'\b.{12}FD9921\b': 'Entrance door',
                                 r'\b.{12}D44FAE\b': 'Entrance motion',
                                 r'\b.{12}2E7EE1\b': 'Laundryoom door'}
                }

EXCLUDE_TEXT = ('RF Bridge 0',
                'rf bridge Motion Livingroom')


async def tcp_send(address, port, data, loop=None):
    reader, writer = await asyncio.open_connection(address, port, loop=loop)
    logger.debug(f'sending {data}')
    writer.write(data.encode())
    data = await reader.read(100)
    logger.debug(f'received: {data.decode()}')
    logger.debug('close the socket')
    writer.close()


def tcp_send_blocking(address, port, data):
    d = data.replace('"', '\\"')
    command = f'echo "{d}" | nc {address} {port}'
    logger.debug(command)
    try:
        r = subprocess.check_output(command, shell=True)
    except subprocess.CalledProcessError:
        logger.warning(f'failed connecting to dummy_display {address}:{port}')
    else:
        logger.debug(r)


def adjust_text(input_payload):
    output_payload = input_payload.replace('\\\n', ' ').lower()
    input_payload = input_payload.replace('\\\n', ' ').lower()
    for match_words, rules in REPLACE_TEXT.items():
        if any((x.lower() in input_payload for x in match_words)):
            for match, word in rules.items():
                output_payload = re.sub(match.lower(), word, output_payload, re.IGNORECASE)
    logger.debug(f'replacing "{input_payload}"" with "{output_payload}"')
    return output_payload


def adjust_display_text(data, adapt_for='dummy_display'):
    e, m = data
    if adapt_for == 'dummy_display':
        e = e.replace(' ', '\\\n')
        display_text = adjust_text(f'{e}\\\n{m}')
    elif adapt_for == 'kodi_display':
        display_text = adjust_text(f'{e} {m}')
    else:
        return None, None, None
    if any([_.lower() in display_text.lower() for _ in EXCLUDE_TEXT]):
        logger.debug(f'discarding message {display_text}')
        return None, None, None
    return e, m, display_text


async def send_dummy_display(address, port, data, display_type='text', loop=None):
    display_types = ('text', 'image')
    if display_type not in display_types:
        raise ValueError('display_type has to be text or image')
    if display_type == 'text':
        e, m, display_text = adjust_display_text(data, adapt_for='dummy_display')
        payload = {'text': {'input_text': display_text}}
        p = json.dumps(payload)
        if not any((x in e for x in ('Bridge',))):
            logger.debug(f'sending message to dummy display {display_text}')
            tcp_send_blocking(address, port, p)


def send_kodi_message(address, port, data):
    from kodijson import Kodi
    e, m, display_text = adjust_display_text(data, adapt_for='kodi_display')
    kodi = Kodi(f'http://{address}:{port}/jsonrpc')
    try:
        logger.debug(f'sending message to Kodi {display_text}')
        time = datetime.datetime.now().strftime('%H:%M')
        kodi.JSONRPC.Ping()
        kodi.GUI.ShowNotification({"title": time, "message": display_text})
    except (ConnectionError,
            ConnectionRefusedError,
            requests.exceptions.ConnectionError,
            urllib3.exceptions.NewConnectionError,
            urllib3.exceptions.MaxRetryError):
        logger.warning(f'Unable to conned to Kodi {address}:{port}')
    except Exception:
        logger.exception('Something unexpected went wrong while sending to Kodi')


async def on_hass_mqtt_message(client, topic, payload, qos, properties):
    logger.debug(f'Incoming MQTT topic:{topic}, payload:{payload}, qos:{qos}, properties:{properties}')
    hass = client.properties.get('hass_ref')
    loop = client._connected._loop
    # hass.attributes = states of entities (entity_id, state)
    if hass:
        entity = hass.get_entity_info(topic)
    else:
        entity = {'name': None}
    if entity:
        e, m = (entity["name"], payload.decode())
        logger.info(f'Processing MQTT message: {e} changed to {m}')
        dummy_display_settings = client.properties['app_config']['dummy_display']
        if dummy_display_settings['enabled']:
            address = dummy_display_settings['address']
            port = dummy_display_settings['port']
            await send_dummy_display(address, port, (e, m), display_type='text', loop=client._connected._loop)
        kodi_display_settings = client.properties['app_config']['kodi_display']
        if kodi_display_settings['enabled']:
            address = kodi_display_settings['address']
            port = kodi_display_settings['port']
            blocking_call = loop.run_in_executor(None, send_kodi_message, address, port, (e, m))
            completed, pending = await asyncio.wait([blocking_call])
    else:
        # run function if one is found in mqtt message
        *_, t = topic.split('/')
        mqtt_functions = client.properties['app_config'].get('mqtt_functions', {})
        if t in mqtt_functions.keys():
            logger.info(f'found {t} in mqtt topic and will run {mqtt_functions[t]}({payload})')
            f = import_item(mqtt_functions[t])
            # f(payload, hass=hass)
            # f_with_args = partial(f, payload, hass=hass)
            logger.debug(f'awaiting {f}')
            await f(payload, hass=hass)
            # task = asyncio.create_task(f_with_args())
            # await loop.run_in_executor(None, f_with_args)
