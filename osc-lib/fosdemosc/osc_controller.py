from typing import List, Mapping
from pythonosc.osc_message_builder import OscMessageBuilder

from dataclasses import dataclass
from collections import defaultdict
import re

from .slip_client import SLIPClient
from .udp_client import ParsingUDPClient

Channel = int
Bus = int
Level = float

SERIAL_READ_TIMEOUT: float | None = 1
SERIAL_WRITE_TIMEOUT: float | None = 1

def padinf(x: float) -> float:
    # Note: checking `math.isinf(x) and x < 0` should be faster
    return -60 if x == float('-inf') else x


def groups(regex, val):
    matches = regex.search(val)
    return matches.groups()

def groups_all(regex, vals):
    for k, v in vals.items():
        matches = regex.search(k)
        if matches:
            yield matches.groups(), k, v

@dataclass
class VUMeter:
    peak: float
    rms: float
    smooth: float

class OSCController:
    __info: Mapping[str, str]

    inputs: List[str]
    outputs: List[str]

    def __send(self, address: str, *args):
        message = OscMessageBuilder(address)
        for arg in args:
            message.add_arg(arg)

        self.client.send(message.build())

        return self.client.receive_obj()

    def __get_info(self) -> Mapping[str,str]:
        response = self.__send("/info")
        return {x.address: x.params[0] for x in response}


    def __get_chbus_name(self, specifier: str, num: int) -> str:
        return self.__info[f"/{specifier}/{num}/config/name"]

    def __get_chbus_multiplier(self, specifier: str, num: int) -> float:
        response = self.__send(f"/{specifier}/{num}/multiplier")
        return float(response.params[0])

    def __set_chbus_multiplier(self, specifier: str, num: int, multiplier: float):
        self.__send(f"/{specifier}/{num}/multiplier", float(multiplier))

    def __get_inputs(self) -> List[str]:
        return [self.__get_chbus_name('ch', x) for x in range(int(self.__info["/info/channels"]))]

    def __get_outputs(self) -> List[str]:
        return [self.__get_chbus_name('bus', x) for x in range(int(self.__info["/info/buses"]))]

    def get_bus_multiplier(self, bus: Bus) -> float:
        return self.__get_chbus_multiplier('bus', bus)

    def set_bus_multiplier(self, bus: Bus, multiplier: float):
        self.__set_chbus_multiplier('bus', bus, multiplier)

    def get_channel_multiplier(self, channel: Channel) -> float:
        return self.__get_chbus_multiplier('ch', channel)

    def set_channel_multiplier(self, channel: Channel, multiplier: float):
        self.__set_chbus_multiplier('ch', channel, multiplier)


    @property
    def device(self) -> str | None:
        return self._device

    def __init__(self, device: str, baud=1152000, mode='serial', read_timeout=SERIAL_READ_TIMEOUT, write_timeout=SERIAL_WRITE_TIMEOUT):
        if mode == 'serial':
            self._device = device
            self.client = SLIPClient(device, baud, timeout=read_timeout, write_timeout=write_timeout)
        elif mode == 'udp':
            self._device = f"{device}:{baud}"
            self.client = ParsingUDPClient(device, baud)
        else:
            raise ValueError('mode')

        self.__initialize()

    def __initialize(self):
        self.__info = self.__get_info()

        self.inputs = self.__get_inputs()
        self.outputs = self.__get_outputs()

    def get_matrix(self) -> List[List[float]]:
        return [[self.get_gain(ch, bus) for bus in range(len(self.outputs))] for ch in range(len(self.inputs))]

    def get_raw_matrix(self) -> List[List[float]]:
        return [[self.get_raw_gain(ch, bus) for bus in range(len(self.outputs))] for ch in range(len(self.inputs))]

    def mute_matrix(self) -> List[List[bool]]:
        return [[bool(self.get_muted(ch, bus)) for bus in range(len(self.outputs))] for ch in range(len(self.inputs))]

    def get_bus_vu_meters(self) -> Mapping[Bus, List[VUMeter]]:
        return {bus: self.get_bus_levels(i) for i, bus in enumerate(self.outputs)}

    def get_channel_vu_meters(self) -> Mapping[Channel, List[VUMeter]]:
        return {ch: self.get_channel_levels(i) for i, ch in enumerate(self.inputs)}

    def get_bus_multipliers(self) -> Mapping[Bus, float]:
        return {bus: self.get_bus_multiplier(i) for i, bus in enumerate(self.outputs)}

    def get_channel_multipliers(self) -> Mapping[Channel, float]:
        return {ch: self.get_channel_multiplier(i) for i, ch in enumerate(self.inputs)}

    def get_gain(self, channel: Channel, bus: Bus) -> Level:
        response = self.__send(f"/ch/{channel}/mix/{bus}/level")
        return Level(response.params[0])

    def get_raw_gain(self, channel: Channel, bus: Bus) -> Level:
        response = self.__send(f"/ch/{channel}/mix/{bus}/raw")
        return Level(response.params[0])

    def set_gain(self, channel: Channel, bus: Bus, level: Level) -> None:
        self.__send(f"/ch/{channel}/mix/{bus}/level", Level(level))

    def get_muted(self, channel: Channel, bus: Bus) -> bool:
        response = self.__send(f"/ch/{channel}/mix/{bus}/muted")
        return bool(response.params[0])

    def set_muted(self, channel: Channel, bus: Bus, muted: bool) -> None:
        self.__send(f"/ch/{channel}/mix/{bus}/muted", bool(muted))

    def get_channel_levels(self, channel: Channel) -> VUMeter:
        response = self.__send(f"/ch/{channel}/levels")
        return VUMeter(**{x.address.rsplit("/", 1)[-1]: padinf(x.params[0]) for x in response})

    def get_bus_levels(self, bus: Bus) -> VUMeter:
        response = self.__send(f"/bus/{bus}/levels")
        return VUMeter(**{x.address.rsplit("/", 1)[-1]: padinf(x.params[0]) for x in response})

    def get_state(self):
        return {
            'mutes': self.get_mutes(),
            'multipliers': {
                'input': self.get_channel_multipliers(),
                'output': self.get_bus_multipliers(),
            },
        }

    def get_mutes(self) -> dict[str, dict[str, bool]]:
        return {ch: {bus: self.get_muted(i, j) for j, bus in enumerate(self.outputs)} for i, ch in enumerate(self.inputs)}

    def reset(self):
        self.__send("/factoryreset")


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
