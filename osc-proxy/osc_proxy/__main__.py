import os.path
import time
from typing import Dict, Any, Union

import logging
import socket
import threading
import queue

from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage

from .slip import SLIPClient

to_serial = queue.Queue()


class UdpClient:
    request: OscMessage

    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.request = None
        self.last = time.time()

    def send(self, content: Union[OscMessage, OscBundle]):
        self.sock.sendto(content.dgram, self.addr)


slip_client = None
udp_client: dict[Any, UdpClient] = dict()


def run_serial(device):
    global slip_client
    log = logging.getLogger('SLIP')
    while True:
        while not os.path.exists(device):
            time.sleep(1)

        client = SLIPClient(device, 1152000)
        slip_client = client
        log.info(f"Opened {device}")

        while not to_serial.empty():
            msg = to_serial.get()
            log.info(f"Replaying queued message: {msg}")
            client.send(msg)

        while True:
            try:
                response = client.receive()
            except Exception as e:
                slip_client = None
                log.error(e)
                log.info("Restarting serial connection")
                break

            log.debug(f"Received: {response}")

            for uc in udp_client.values():
                if uc.request.address == response.address:
                    uc.send(response)


def run_proxy(bind_to, port=10024):
    global udp_client
    log = logging.getLogger('OSC ')
    log.info(f"Running proxy on UDP {bind_to}:{port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_to, port))
    sock.settimeout(3)

    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except TimeoutError:
            # No commands received for 3 seconds, run cleanup instead
            for addr in list(udp_client.keys()):
                if udp_client[addr].last < time.time() - 10:
                    log.info(f'Client {addr} disconnected')
                    del udp_client[addr]
            continue

        if addr not in udp_client:
            log.info(f"New client: {addr}")
            udp_client[addr] = UdpClient(sock, addr)
        else:
            udp_client[addr].last = time.time()

        msg = OscMessage(data)
        udp_client[addr].request = msg
        log.debug(f"{addr}: {msg}")

        if slip_client is None:
            log.warning("Packet received while uart is disconnected")
            to_serial.put(msg)
            continue
        slip_client.send(msg)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Serial to socket bridge for OSC")
    parser.add_argument("uart")
    parser.add_argument("--port", "-p", type=int, default=10024, help="Port to bind to (defaults to 10024)")
    parser.add_argument("--bind", "-b", default="127.0.0.1", help="Address to bind to (defaults to 0.0.0.0)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(name)s :: %(levelname)s :: %(message)s'))
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, handlers=[ch])

    uart_thread = threading.Thread(target=run_serial, args=(args.uart,))
    uart_thread.daemon = True
    osc_thread = threading.Thread(target=run_proxy, args=(args.bind, args.port))
    osc_thread.daemon = True

    uart_thread.start()
    osc_thread.start()

    osc_thread.join()


if __name__ == "__main__":
    main()
