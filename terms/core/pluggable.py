
from importlib import import_module

import terms.core.schemata
import terms.core


def get_plugin_names(config):
    plugins = []
    if 'plugins' in config:
        plugins = [p for p in config['plugins'].strip().split('\n') if p]
    return plugins


def get_plugins(config):
    names = get_plugin_names(config)
    return [import_module(p) for p in names]


def init_environment(config):
    plugins = get_plugin_names(config)
    for plugin in plugins:
        schemata = import_module(plugin + '.schemata')
        terms.core.schemata.__dict__.update(schemata.__dict__)
        exec_globals = import_module(plugin + '.exec_globals')
        terms.core.exec_globals.update(exec_globals.__dict__)
