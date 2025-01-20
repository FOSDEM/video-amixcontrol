from fosdemosc import OSCController, parse_bus, parse_channel, parse_level
from fosdemosc import VUMeter

def connect_osc(config) -> OSCController:
#    logger.info(f"Connecting to serial {config['conn']}")
    if 'device' in config['conn'] and config['conn']['device']:
        osc = OSCController(config['conn']['device'])
#        logger.info(f"Created serial connection to {config['conn']['device']}")
    else:
        osc = OSCController(config['conn']['host'], config['conn']['port'], mode='udp')
#        logger.info(f"Connected to UDP {config['conn']['host']}:{config['conn']['port']}")

    return osc
