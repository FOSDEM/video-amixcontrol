#!/usr/bin/env python3

import os
import os.path
import time
from typing import Dict, Any, Union
from dataclasses import dataclass

import logging
import socket
import multiprocessing
from queue import SimpleQueue
import select

from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message import OscMessage

import serial
from .helpers import parse_osc_bytes
from .slip_client import SLIPClient

class UdpClient:
    def __init__(self, sock, addr):
        self.sock = sock
        self.addr = addr
        self.last = time.time()

    def send(self, content: OscMessage | OscBundle):
        self.sock.sendto(content.dgram, self.addr)


@dataclass
class DataItem:
    host: UdpClient
    data: OscMessage | OscBundle

def dictify(obj: OscMessage | OscBundle | None):
    if obj is None:
        return None
    elif isinstance(obj, OscBundle):
        return {x.address: x.params[0] if len(x.params) else None for x in obj}
    else:
        return {obj.address: obj.params[0] if len(obj.params) else None}


def run_serial(requests, responses, device):
    log = logging.getLogger('SLIP')

    slip_client = None

    while True:
        while not os.path.exists(device):
            time.sleep(1)

        if not slip_client:
            try:
                slip_client = SLIPClient(device, baud=1152000, timeout=1, write_timeout=1)
                log.info(f"Opened {device}")
                time.sleep(0.5)
            except Exception as e:
                slip_client = None
                log.error(e)
                log.info("Restarting serial connection")
                continue

        try:
            msg = requests.get()
            log.debug(f"Sending queued message: {dictify(msg.data)}")
            slip_client.send(msg.data)

            response = slip_client.receive_obj()
            log.debug(f"Received response for {msg.host.addr}: {dictify(response)}")

            responses.put(DataItem(host=msg.host, data=response))
        except serial.SerialTimeoutException:  # commands don't return a result
            log.error(f"BUGBUG: Command from {msg.host.addr} without a response: {dictify(msg.data)}")
            log.error(f"Either mixer firmware is too old, or it is dead")
        except Exception as e:
            slip_client = None
            log.warn("Restarting serial connection, requeueing message")
            requests.put(msg)

        # No messages in queue, we can use it to push something to all clients if we want
        pass

def run_udp_sender(requests, responses):
    log = logging.getLogger('UDPS')

    while True:
        msg = responses.get()
        log.debug(f"Sending queued message {dictify(msg.data)} to {msg.host.addr}")
        msg.host.send(msg.data)

def run_udp_listener(requests, responses, bind_to, port=10024):
    log = logging.getLogger('UDPL')
    log.info(f"Running proxy on UDP {bind_to}:{port}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_to, port))
    sock.setblocking(False)


    while True:
        waiting, _, _ = select.select([sock], [], [])

        if not sock in waiting:
            continue

        try:
            data, addr = sock.recvfrom(1024)
            log.debug(f"Received message from {addr}")
        except TimeoutError:
            # No commands received for 3 seconds, run cleanup instead
            continue

        osc_data = parse_osc_bytes(data)

        requests.put(DataItem(host=UdpClient(sock, addr), data=osc_data))
        log.debug(f"queued request from {addr}: {dictify(osc_data)}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Serial to socket bridge for OSC")
    parser.add_argument("--uart", "-u", type=str, default='/dev/tty_fosdem_audio_ctl', help="Serial port to bind to (defaults to /dev/tty_fosdem_audio_ctl)")
    parser.add_argument("--port", "-p", type=int, default=10024, help="Port to bind to (defaults to 10024)")
    parser.add_argument("--bind", "-b", default="127.0.0.1", help="Address to bind to (defaults to 127.0.0.1)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(name)s :: %(levelname)s :: %(message)s'))
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, handlers=[ch])

    requests = multiprocessing.Queue()
    responses = multiprocessing.Queue()

    uart_process = multiprocessing.Process(target=run_serial, args=(requests, responses, args.uart,))
    uart_process.start()
    udp_listen_process = multiprocessing.Process(target=run_udp_listener, args=(requests, responses, args.bind, args.port,))
    udp_listen_process.start()
    udp_send_process = multiprocessing.Process(target=run_udp_sender, args=(requests, responses,))
    udp_send_process.start()

    log = logging.getLogger('CTRL')

    log.info(f'Controller PID {os.getpid()}')
    log.info(f'UART PID {uart_process.pid}')
    log.info(f'Listener PID {udp_listen_process.pid}')
    log.info(f'Sender PID {udp_send_process.pid}')

    uart_process.join()


if __name__ == "__main__":
    main()
