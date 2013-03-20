
from importlib import import_module

import terms.core


def get_plugin_names(config):
    plugins = []
    if 'plugins' in config:
        plugins = [p for p in config['plugins'].strip().split('\n') if p]
    return plugins


def get_plugins(config):
    names = get_plugin_names(config)
    return [import_module(p) for p in names]


def load_plugins(config):
    plugins = get_plugin_names(config)
    for plugin in plugins:
        exec_globals = import_module(plugin + '.exec_globals')
        terms.core.exec_globals.update(exec_globals.__dict__)
