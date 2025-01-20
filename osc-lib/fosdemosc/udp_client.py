from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage
from pythonosc.udp_client import UDPClient

from .helpers import parse_osc_bytes


class ParsingUDPClient(UDPClient):
    def receive_obj(self, *args, **kwargs) -> OscBundle | OscMessage:
        return parse_osc_bytes(self.receive(*args, **kwargs))
