from loguru import logger

# from hass_assister.__main__ import hass


def on_hass_mqtt_message(client, topic, payload, qos, properties):
    hass = client.properties.get('hass_ref')
    if hass:
        entity = hass.get_entity_info(topic)
    else:
        entity = {'name': None}
    if entity:
        logger.info(f'Processing MQTT message: {entity["name"]} changed to {payload.decode()}')
    else:
        logger.debug(f'Processing MQTT message: {topic} {payload}')
