from .osc_controller import OSCController, Bus, Channel, Level
from collections import defaultdict


def parse_bus(osc: OSCController, bus: str | int) -> Bus:
    if isinstance(bus, int) or bus.isdecimal():
        if Bus(bus) < len(osc.outputs):
            return Bus(bus)
        raise ValueError(f"Only {len(osc.inputs)} buses exist, but {bus} requested")

    else:  # not bus.isdecimal():
        for i, x in enumerate(osc.outputs):
            if x.lower().strip() == bus.lower().strip() or x.lower().replace(" ", "").strip() == bus.lower().strip():
                return Bus(i)

        raise ValueError(f"Bus {bus} does not exist")

def parse_channel(osc: OSCController, channel: str | int) -> Channel | None:
    if isinstance(channel, int) or channel.isdecimal():
        if Channel(channel) < len(osc.inputs):
            return Channel(channel)
        raise ValueError(f"Only {len(osc.inputs)} channels exist, but {channel} requested")

    else:  # not channel.isdecimal()
        for i, x in enumerate(osc.inputs):
            if x.lower().strip() == channel.lower().strip() or x.lower().replace(" ", "").strip() == channel.lower().strip():
                return Channel(i)

        raise ValueError(f"Channel {channel} does not exist")

def parse_level(osc: OSCController, level: str | float) -> Level:
    return Level(level)
