from fosdemosc import OSCController, parse_bus, parse_channel, parse_level
from fosdemosc import VUMeter

from fastapi.websockets import WebSocket, WebSocketDisconnect
from asyncio import Event

def connect_osc(config) -> OSCController:
    if 'device' in config['conn'] and config['conn']['device']:
        osc = OSCController(config['conn']['device'])
    else:
        osc = OSCController(config['conn']['host'], config['conn']['port'], mode='udp')

    return osc

def strtobool (val):
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
