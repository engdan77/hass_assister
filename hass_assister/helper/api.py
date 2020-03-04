import importlib


def import_item(item):
    if type(item) is str:
        *module, attr = item.split(".")
        if not module:
            f = globals()[attr]
        else:
            f = getattr(importlib.import_module(".".join(module)), attr)
    else:
        f = item
    return f
