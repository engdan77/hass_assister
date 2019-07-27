from loguru import logger
import asyncio


async def tcp_send(address, port, data, loop=None):
    reader, writer = await asyncio.open_connection(address, port, loop=loop)
    logger.debug(f'sending {data}')
    writer.write(data.encode())
    data = await reader.read(100)
    logger.debug(f'received: {data.decode()}')
    logger.debug('close the socket')
    writer.close()


async def send_dummy_display(address, port, data, display_type='text', loop=None):
    display_types = ('text', 'image')
    if not display_type in display_types:
        raise ValueError('display_type has to be text or image')

    if display_type == 'text':
        e, m = data
        await tcp_send(address, port, f'{e}\\n{m}', loop=loop)


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
    else:
        logger.debug(f'Processing MQTT message: {topic} {payload}')
