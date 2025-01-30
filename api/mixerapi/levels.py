from fosdemosc import OSCController

import urllib.parse

import requests

import socket

import math
import itertools
import dataclasses

import multiprocessing
import time

from . import helpers

import logging

logger = logging.getLogger("levels")

def start(config, web_state, manager = multiprocessing.Manager()):
    global influxdb_state
    influxdb_state = helpers.StateEvent(manager.Event(), manager.dict())

    poller_process = multiprocessing.Process(target=poll_levels, args=(config, web_state, influxdb_state,))
    influx_process = multiprocessing.Process(target=push_influxdb, args=(config, influxdb_state,))

    return (poller_process, influx_process)

def poll_levels(config, web_state, influx_state):
    osc = helpers.connect_osc(config)
    logger.info(f"Connected to {osc.device}")

    int_web = config['levels']['interval_web']
    int_influxdb = config['levels']['interval_influx']

    poll_base = math.gcd(int_web, int_influxdb)
    poll_count = math.lcm(int_web, int_influxdb)

    mult_web = poll_base / int_web
    mult_influxdb = poll_base / int_influxdb

    # like `while True`, but counts the cycle, and keeps it from overflowing
    for i in itertools.cycle(range(poll_count)):
        time.sleep(poll_base / 1000)
        levels = helpers.get_all_levels(osc)

        if not levels:
            continue

        if i % mult_web == 0 and not web_state.is_set():
            web_state.set(lambda x: helpers.merge(x, levels))

        if i % mult_influxdb == 0 and not influx_state.is_set():
            influx_state.set(lambda x: helpers.merge(x, levels))

def push_influxdb(config, influxdb_state):
    if not ('influx_host' and 'influx_db') in config['levels']:
        logger.info('no influx')
        return

    host = config['levels']['influx_host']
    db = config['levels']['influx_db']

    url = urllib.parse.urlunsplit(('http', host, '/write', f'db={db}', ''))

    hostname = socket.gethostname()

    while True:
        levels = influxdb_state.get()

        data = '\n'.join(
                [f'input_levels,box={hostname},ch={ch} rms={vu["rms"]},peak={vu["peak"]},smooth={vu["smooth"]}' 
                 for ch, vu in levels['input'].items()] +
                [f'output_levels,box={hostname},bus={bus} rms={vu["rms"]},peak={vu["peak"]},smooth={vu["smooth"]}' 
                 for bus, vu in levels['output'].items()])

        requests.post(url, data=data.encode())
