import aiohttp

class HassInstance(object):
    def __init__(self, url, auth_token, ap_scheduler=None):
        self.url = url
        self.auth_token = auth_token
        self.scheduler = ap_scheduler
        self.sensors = None

    async def get_sensor_status(self):
        async with aiohttp.ClientSession() as s, s.get(self.url, headers={'Authorization': f'Bearer {self.auth_token}'}) as response:
            r = await response.read()
            logger.info(r)

