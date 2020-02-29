from unittest.mock import MagicMock
import sys
sys.modules['paho'] = MagicMock()
sys.modules['paho.mqtt.client'] = MagicMock()
import os
import json
import time
import requests
from hass_assister.controllers.pylips import Pylips
from kodijson import Kodi
from loguru import logger
import asyncio
from wakeonlan import send_magic_packet
import urllib3
from functools import partial


class MyPylips(Pylips):
    def __init__(self, host='10.1.1.4', user='EhlqVjhh0aoAdYMR', pwd='3975436a69392115aee33573aef4dbe7e59c79f5a61ae681008075e46911b3e3', mac='54:2A:A2:C8:3A:EE'):
        self.mac = mac
        self.host = host
        self.config = {
            'DEFAULT': {
                'verbose': True,
                'num_retries': 3,
                'update_interval': 3,
                'mqtt_listen': 'False'
            },
            'TV': {
                'host': host,
                'port': 1926,
                'apiv': 6,
                'user': user,
                'pass': pwd,
                'protocol': 'https://'
            }
        }

        # load API commands
        with open(os.path.dirname(os.path.realpath(__file__))+"/available_commands.json") as json_file:
            self.available_commands = json.load(json_file)

    def my_start(self):
        logger.info(f'will attempt to WakeOnLan on mac "{self.mac}" the type {type(self.mac)} is same {"54:2A:A2:C8:3A:EE" == self.mac}')
        # send_magic_packet('54:2A:A2:C8:3A:EE')
        send_magic_packet(self.mac)
        time.sleep(5)
        url = f'http://{self.host}:8008/apps/ChromeCast'
        logger.debug(f'attempt to wake TV by ChromeCast using url {url}')
        requests.post(url)
        time.sleep(1)
        power_state = self.run_command("powerstate").lower()
        logger.debug(f'my_start: {power_state}')
        if 'error' in power_state:
            logger.warning(f'error occurred while starting tv')
            time.sleep(1)
            logger.debug('will try power_on instead')
            try:
                self.run_command('allow_power_on')
                time.sleep(2)
                self.run_command('power_on')
            except (OSError,
                    requests.exceptions.ConnectTimeout,
                    urllib3.exceptions.NewConnectionError,
                    urllib3.exceptions.MaxRetryError,
                    requests.exceptions.ConnectionError) as e:
                logger.info(f'unable to connect to TV with {e}')
                requests.post()
            time.sleep(10)
            logger.debug('trying to get power state again')
            power_state = self.run_command("powerstate").lower()
            logger.debug(f'power state now being {power_state}')
            return 'error' not in power_state
        if 'standby' in power_state:
            logger.debug('starting tv')
            self.run_command('standby')
            time.sleep(10)
        if 'on' in power_state:
            logger.debug('tv already on')
            time.sleep(3)
        power_state = self.run_command("powerstate").lower()
        logger.debug(f'tv status after start {power_state}')
        return True

    def my_launch_kodi(self, max_time=10):
        for _ in range(max_time):
            logger.debug(f'my_launch_kodi: waiting for TV to start {_}/{max_time}')
            logger.debug(f'my_launch_kodi: {self.run_command("powerstate").lower()}')
            if 'on' in self.run_command('powerstate').lower():
                break
            time.sleep(2)
            if _ == max_time - 1:
                logger.debug('timed out')
                return
        if not 'kodi' in self.run_command('current_app').lower():
            self.run_command('launch_app',
                           '{"id":"org.xbmc.kodi","order":0,"intent":{"action":"Intent{act=android.intent.action.MAIN cat=[android.intent.category.LAUNCHER] flg=0x10000000 pkg=org.xbmc.kodi }","component":{"packageName":"org.xbmc.kodi","className":"org.xbmc.kodi.Splash"}},"label":"Kodi"}')

    def my_turn_off(self):
        if 'on' in self.run_command('powerstate').lower():
            self.run_command('standby')


class MyKodi():
    def __init__(self, url='http://10.1.1.4:8080/jsonrpc'):
        self.kodi = Kodi(url)

    def wait_until_started(self, max_time=10):
        for _ in range(max_time):
            logger.debug(f'attempt {_}/{max_time}')
            try:
                ping = self.kodi.JSONRPC.Ping()
                if ping['result'] == 'pong':
                    return True
            except requests.exceptions.ConnectionError:
                pass
            time.sleep(5)
        return False

    def open_media(self, url=''):
        time.sleep(1)
        self.kodi.Player.Open(item={"file": url.decode() if isinstance(url, bytes) else url})

    def open_channel(self, channel_id=0):
        time.sleep(1)
        self.kodi.Player.Open(item={"channelid": channel_id})


async def start_media(message='smb://foo/bar.mp4', **kwargs):
    loop = asyncio.get_running_loop()
    logger.debug(f'tv start media arg: {message}')
    c = kwargs.get('app_config', None)
    tv = await loop.run_in_executor(None, MyPylips, c['philips_ip'], c['philips_user'], c['philips_password'], c['philips_mac'])
    logger.debug('starting tv')
    tv_started = await loop.run_in_executor(None, tv.my_start)
    if not tv_started:
        logger.warning('abort starting kodi due to tv not started')
        return False
    logger.debug('starting kodi')
    await loop.run_in_executor(None, tv.my_launch_kodi)
    kodi = await loop.run_in_executor(None, MyKodi)
    logger.debug('waiting for kodi to start')
    status = await loop.run_in_executor(None, kodi.wait_until_started)
    if status is False:
        logger.debug('kodi not started in time')
        return
    logger.debug(f'starting media {message}')
    await loop.run_in_executor(None, kodi.open_media, message)
    return True


async def start_channel(message='1', **kwargs):
    loop = asyncio.get_running_loop()
    logger.debug(f'tv start channel arg {message}')
    # TODO: Add arguments user, password and mac to tv
    mypylips_with_args = partial(MyPylips, host='', user='', pwd='', mac='')
    tv = await loop.run_in_executor(None, MyPylips)
    await loop.run_in_executor(None, tv.my_start)
    await loop.run_in_executor(None, tv.my_launch_kodi)
    kodi = await loop.run_in_executor(None, MyKodi)
    status = await loop.run_in_executor(None, kodi.wait_until_started)
    if status is False:
        return
    await loop.run_in_executor(None, kodi.open_channel, int(message))
    # To find channel: kodi.Player.GetItem(playerid=1)


async def command(message='turn_off', **kwargs):
    loop = asyncio.get_running_loop()
    logger.debug(f'tv command arg {message}')
    if 'turn_off' in message.decode():
        tv = await loop.run_in_executor(None, MyPylips)
        await loop.run_in_executor(None, tv.my_turn_off)
