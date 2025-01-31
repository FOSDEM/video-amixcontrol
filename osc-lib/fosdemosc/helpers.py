from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle


def parse_osc_bytes(contents: bytes) -> OscMessage | OscBundle:
        bundlestr = b'#bundle\0'

        if contents.startswith(bundlestr):
            return OscBundle(contents)
        else:
            return OscMessage(contents)
