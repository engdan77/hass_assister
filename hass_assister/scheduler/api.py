from typing import Optional, List, Dict, Tuple
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import importlib
import sys
import warnings
from loguru import logger
from hass_assister.helper import import_item

# Used to overcome "found in sys.modules after import of package .."
if not sys.warnoptions:  # allow overriding with `-W` option
    warnings.filterwarnings('ignore', category=RuntimeWarning, module='runpy')

class MyScheduler(object):
    def __init__(self,
                 initials: List[Tuple[str, str, Dict]],
                 schedule_queue: Optional[asyncio.Queue] = None) -> None:
        self.scheduler = AsyncIOScheduler()

        if schedule_queue is None:
            self.queue = schedule_queue
        else:
            self.queue = asyncio.Queue()

        self.add_initials(initials)
        self.scheduler.start()

    def add_task(self, _func, _type, **kwargs):
        logger.info(f'adding scheduling for {_func} with {kwargs}')
        f = import_item(_func)
        self.scheduler.add_job(f, _type, **kwargs)  # special trick to allow calling attr within other package


    def add_initials(self, initials):
        for _func, _type, kwargs in initials:
            self.add_task(_func, _type, **kwargs)
