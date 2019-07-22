import functools
import os
from pathlib import Path

import easyconf
from appdirs import user_config_dir
from loguru import logger


def init_settings(_default_config_params):
    p = globals().get('__package__')
    local_config_dir = next(iter([d / 'config' for d in list(Path(os.path.abspath(__file__)).parents)[:2] if (d / 'config').exists()]), None)
    if local_config_dir and local_config_dir.exists():
        logger.info(f'found local config directory in {local_config_dir}')
        base_config_dir = local_config_dir
    else:
        base_config_dir = user_config_dir(p)
        logger.info(f'no local config directory, creating settings in {base_config_dir}')
    conf_path = Path(base_config_dir) / Path(f'{p}.yaml')
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"creating {conf_path}")
    conf_obj = easyconf.Config(str(conf_path))
    conf = {}
    for param, initials in _default_config_params.items():
        conf[param] = functools.partial(getattr(conf_obj, param), **initials)()
    logger.info(f'configuration loaded {conf}')
    return conf