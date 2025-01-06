from typing import List
from pythonosc.osc_message_builder import OscMessageBuilder

from .slip_client import SLIPClient

Channel = int
Bus = int
Level = float

SERIAL_READ_TIMEOUT: float | None = 1
SERIAL_WRITE_TIMEOUT: float | None = 1

NUM_CHANNELS = 6
NUM_BUSES = 6

class OSCController:
    inputs: List[str]
    outputs: List[str]
#    inputs = ['IN1', 'IN2', 'IN3', 'PC', 'USB1', 'USB2']
#    outputs = ['OUT1', 'OUT2', 'HP1', 'HP2', 'USB1', 'USB2']

    def __get_chbus_name(self, specifier: str, num: int) -> str:
        message = OscMessageBuilder(f"/{specifier}/{num}/config/name")
        self.client.send(message.build())
        response = self.client.receive_message()
        return str(response.params[0])

    def __get_chbus_multiplier(self, specifier: str, num: int) -> float:
        message = OscMessageBuilder(f"/{specifier}/{num}/multiplier")
        self.client.send(message.build())
        response = self.client.receive_message()
        return float(response.params[0])

    def __set_chbus_multiplier(elf, specifier: str, num: int, multiplier: float):
        message = OscMessageBuilder(f"/{specifier}/{num}/multiplier")
        message.add_arg(float(multiplier))
        self.client.send(message.build())

    def __get_inputs(self) -> List[str]:
        return [self.__get_chbus_name('ch', x) for x in range(0, NUM_CHANNELS)]

    def __get_outputs(self) -> List[str]:
        return [self.__get_chbus_name('bus', x) for x in range(0, NUM_BUSES)]

    @property
    def device(self) -> str:
        return self._device

    def __init__(self, device, baud=1152000, read_timeout=SERIAL_READ_TIMEOUT, write_timeout=SERIAL_WRITE_TIMEOUT):
        self._device = device
        self.client = SLIPClient(device, baud, timeout=read_timeout, write_timeout=write_timeout)

        self.inputs = self.__get_inputs()
        self.outputs = self.__get_outputs()

    def get_matrix(self) -> List[List[float]]:
        return [[self.get_gain(ch, bus) for bus in range(0, 6)] for ch in range(0, 6)]

    def get_gain(self, channel: Channel, bus: Bus) -> Level:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/level")
        self.client.send(message.build())

        response = self.client.receive_message()
        return Level(response.params[0])

    def get_bus_multiplier(self, bus: Bus) -> Level:
        return __get_chbus_multiplier('bus', bus)

    def get_channel_multiplier(self, channel: Channel) -> Level:
        return __get_chbus_multiplier('ch', channel)

    def get_raw_gain(self, channel: Channel, bus: Bus) -> Level:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/raw")
        self.client.send(message.build())

        response = self.client.receive_message()
        return Level(response.params[0])

    def set_gain(self, channel: Channel, bus: Bus, level: Level) -> None:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/level")
        message.add_arg(Level(level))
        self.client.send(message.build())

    def get_muted(self, channel: Channel, bus: Bus) -> bool:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/muted")
        self.client.send(message.build())

        response = self.client.receive_message()
        return bool(response.params[0])

    def set_muted(self, channel: Channel, bus: Bus, muted: bool) -> None:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/muted")
        message.add_arg(bool(muted))
        self.client.send(message.build())

    def get_state(self):
        message = OscMessageBuilder(f"/state")
        self.client.send(message.build())

        response = self.client.receive_bundle()

        return {x.address: x.params[0] for x in response}

