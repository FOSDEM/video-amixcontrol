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
        return response.params[0]

    def __get_channel_name(self, num: int) -> str:
        return self.__get_chbus_name('ch', num)


    def __get_inputs(self) -> List[str]:
        return [self.__get_channel_name(x) for x in range(0, NUM_CHANNELS)]

    def __get_bus_name(self, num: int) -> str:
        return self.__get_chbus_name('bus', num)

    def __get_outputs(self) -> List[str]:
        return [self.__get_bus_name(x) for x in range(0, NUM_BUSES)]

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
        level = response.params[0]

        return level

    def set_gain(self, channel: Channel, bus: Bus, level: Level) -> None:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/level")
        message.add_arg(Level(level))
        self.client.send(message.build())

        assert abs(self.get_gain(channel, bus) - level) < 0.01  # up to 1% error
