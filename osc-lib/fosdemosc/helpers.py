from .osc_controller import OSCController, Bus, Channel, Level


def parse_bus(osc: OSCController, bus: str) -> Bus:
    if not bus.isdigit():
        return [x.lower() for x in osc.outputs].index(bus.lower())
    else:
        return Bus(bus)


def parse_channel(osc: OSCController, channel: str) -> Channel:
    if not channel.isdigit():
        return [x.lower() for x in osc.inputs].index(channel.lower())
    else:
        return Channel(channel)


def parse_level(osc: OSCController, level: str) -> Level:
    return Level(level)
