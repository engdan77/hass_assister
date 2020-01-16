import importlib


def import_item(item):
    if type(item) is str:
        module, attr = item.rsplit('.') if '.' in item else (None, item)
        if not module:
            f = globals()[attr]
        else:
            f = getattr(importlib.import_module(module), attr)
    else:
        f = item
    return f

