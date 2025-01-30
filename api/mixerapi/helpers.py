import multiprocessing

from fosdemosc import OSCController, parse_bus, parse_channel, parse_level
from fosdemosc import VUMeter

from fastapi.websockets import WebSocket, WebSocketDisconnect
from asyncio import Event

import dataclasses

def connect_osc(config) -> OSCController:
    if 'device' in config['conn'] and config['conn']['device']:
        osc = OSCController(config['conn']['device'])
    else:
        osc = OSCController(config['conn']['host'], config['conn']['port'], mode='udp')

    return osc

def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return True
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))

def merge(old, new):
    for k in old.keys():
        old[k].update(new[k])

    old.update(new)

def dicted(x):
    return {k: dataclasses.asdict(v) for k, v in x.items()}

def get_all_levels(osc: OSCController):
    try:
        ch = osc.get_channel_vu_meters()
        bus = osc.get_bus_vu_meters()

        return ({'input': dicted(ch), 'output': dicted(bus)})
    except:
        return None


class StateEvent:
    def __init__(self, event, data):
        self.event = event
        self.data = data

    def is_set(self):
        return self.event.is_set()

    def set(self, f):
        f(self.data)
        self.event.set()

    def get(self, timeout=None):
        self.event.wait()
        self.event.clear()
        return self.data

    def get_copy(self, timeout=None):
        return self.get(timeout).copy()
