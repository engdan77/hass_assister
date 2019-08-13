from loguru import logger
import subprocess
import json
import re
import asyncio
import urllib3
import requests

REPLACE_TEXT = {('light', 'coffee'): {r'\b1\b': 'ON',
                                      r'\b0\b': 'OFF'}}


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
    output_payload = input_payload
    for match_words, rules in REPLACE_TEXT.items():
        if any((x in input_payload.lower() for x in match_words)):
            for match, word in rules.items():
                output_payload = re.sub(match, word, input_payload, re.IGNORECASE)
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
    from kodijson import Kodi, PLAYER_VIDEO
    e, m, display_text = adjust_display_text(data, adapt_for='kodi_display')
    kodi = Kodi(f'http://{address}:{port}/jsonrpc')
    try:
        logger.debug(f'sending message to Kodi {display_text}')
        ping = kodi.JSONRPC.Ping()
        kodi.GUI.ShowNotification({"title": "", "message": display_text})
    except (ConnectionError,
            ConnectionRefusedError,
            requests.exceptions.ConnectionError,
            urllib3.exceptions.NewConnectionError,
            urllib3.exceptions.MaxRetryError):
        logger.warning(f'Unable to conned to Kodi {address}:{port}')
    except Exception:
        logger.exception('Something unexpected went wrong while sending to Kodi')


async def on_hass_mqtt_message(client, topic, payload, qos, properties):
    hass = client.properties.get('hass_ref')
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
            loop = client._connected._loop
            blocking_call = loop.run_in_executor(None, send_kodi_message, address, port, (e, m))
            completed, pending = await asyncio.wait([blocking_call])
    else:
        logger.debug(f'Processing MQTT message: {topic} {payload}')
