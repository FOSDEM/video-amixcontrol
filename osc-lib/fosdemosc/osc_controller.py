from typing import List

from pythonosc.osc_message_builder import OscMessageBuilder

from .slip_client import SLIPClient

Channel = int
Bus = int
Level = float


class OSCController:
    inputs = ['IN1', 'IN2', 'IN3', 'PC', 'USB1', 'USB2']
    outputs = ['OUT1', 'OUT2', 'HP1', 'HP2', 'USB1', 'USB2']

    @property
    def device(self) -> str:
        return self._device

    def __init__(self, device, baud=1152000):
        self._device = device
        self.client = SLIPClient(device, baud)

    def get_matrix(self) -> List[List[float]]:
        return [[self.get_gain(ch, bus) for bus in range(0, 6)] for ch in range(0, 6)]

    def get_gain(self, channel: Channel, bus: Bus) -> Level:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/level")
        self.client.send(message.build())

        response = self.client.receive()
        level = response.params[0]

        return level

    def set_gain(self, channel: Channel, bus: Bus, level: Level) -> None:
        message = OscMessageBuilder(f"/ch/{channel}/mix/{bus}/level")
        message.add_arg(Level(level))
        self.client.send(message.build())

        assert abs(self.get_gain(channel, bus) - level) < 0.01  # up to 1% error
