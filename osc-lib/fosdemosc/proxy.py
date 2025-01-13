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

#requests: SimpleQueue[DataItem] = SimpleQueue()
#responses: SimpleQueue[DataItem] = SimpleQueue()

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
            except Exception as e:
                slip_client = None
                log.error(e)
                log.info("Restarting serial connection")
                continue


        msg = requests.get()
        log.debug(f"Sending queued message: {msg}")
        slip_client.send(msg.data)

        #  while True:
        try:
            response = slip_client.receive_obj()
            log.debug(f"Received: {response}")

            responses.put(DataItem(host=msg.host, data=response))
        except Exception as e:
            slip_client = None
            log.error(e)
            log.info("Restarting serial connection, requeueing message")
            requests.put(msg)
            continue

        # No messages in queue, we can use it to push something to all clients if we want
        pass

def run_udp_sender(requests, responses):
    log = logging.getLogger('UDPS')

    while True:
        msg = responses.get()
        log.debug(f"Sending queued message to {msg.host}")
        msg.host.send(msg.data)

def run_udp_listener(requests, responses, bind_to, port=10024):
    udp_client: dict[Any, UdpClient] = dict()

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

        osc_data = parse_osc_bytes(data)

        requests.put(DataItem(host=udp_client[addr], data=osc_data))
        log.debug(f"{addr}: {osc_data}")

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

    #run_serial(args.uart)

    #uart_thread.join()
    uart_process.join()


if __name__ == "__main__":
    main()
