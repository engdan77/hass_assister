import aiohttp

class HassInstance(object):
    async def __init__(self, url, auth_token):
        async with aiohttp.ClientSession() as s, s.get(url, headers={'Authorization': f'Bearer {token}'}) as response:
            r = await response.read()
            logger.info(r)

