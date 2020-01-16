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


class MyPylips(Pylips):
    def __init__(self, host='10.1.1.4', user='EhlqVjhh0aoAdYMR', pwd='3975436a69392115aee33573aef4dbe7e59c79f5a61ae681008075e46911b3e3'):
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
        if 'standby' in self.run_command('powerstate').lower():
            logger.debug('starting tv')
            self.run_command('standby')
            time.sleep(3)
        else:
            logger.debug('tv already on')

    def my_launch_kodi(self, max_time=10):
        for _ in range(max_time):
            logger.debug(f'waiting for TV to start {_}/{max_time}')
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
        if self.run_command('powerstate') == 'On':
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

    def open_media(self, url='smb://10.1.1.5/multimedia/Mixed/Fire-Fish/Fireplace.mkv'):
        time.sleep(1)
        self.kodi.Player.Open(item={"file": url})


def start_fire(message):
    logger.debug(f'start_fire arg {message}')
    tv = MyPylips()
    tv.my_start()
    tv.my_launch_kodi()
    kodi = MyKodi()
    kodi.wait_until_started()
    kodi.open_media()




