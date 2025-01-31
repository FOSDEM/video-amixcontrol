from fosdemosc import OSCController

import urllib.parse
import requests
import time

import multiprocessing

import socket

import math
import itertools
import dataclasses

from . import helpers

import logging

logger = logging.getLogger("state")

def start(config, web_state_real, manager = multiprocessing.Manager()):
    global web_state
    global influxdb_state
    influxdb_state = helpers.StateEvent(manager.Event(), manager.dict())
    web_state = web_state_real

    poller_process = multiprocessing.Process(target=poll_state, args=(config, web_state, influxdb_state,))
    influx_process = multiprocessing.Process(target=push_influxdb, args=(config, influxdb_state,))

    return (poller_process, influx_process)

def poll_state(config, web_state, influx_state):
    osc = helpers.connect_osc(config)
    logger.info(f"Connected to {osc.device}")

    int_web = config['state']['interval_web']
    int_influxdb = config['state']['interval_influx']

    gcd = math.gcd(int_web, int_influxdb)
    lcm = math.lcm(int_web, int_influxdb)

    # interval between polling cycles
    poll_base = gcd

    # how often will they get in sync
    poll_count = lcm // gcd

    mult_web = int_web // gcd
    mult_influxdb = int_influxdb // gcd

    logger.info(f"Polling cycles: {poll_count}, each {poll_base} ms, web every {mult_web}, influxdb every {mult_influxdb}")

    # like `while True`, but counts the cycle, and keeps it from overflowing
    for i in itertools.cycle(range(poll_count)):
        time.sleep(poll_base / 1000)
        state = osc.get_state()

        if not state:
            logger.error('No state from mixer')
            continue

        if i % mult_web == 0:
            logger.debug('polling web')
            if web_state.is_set():
                logger.debug('no web clients to update')
            else:
                web_state.set(lambda x: helpers.merge(x, state))

        if i % mult_influxdb == 0:
            logger.debug('polling influxdb')
            if influx_state.is_set():
                logger.warn('influxdb still waiting')
            else:
                influx_state.set(lambda x: helpers.merge(x, state))


def push_influxdb(config, influxdb_state):
    if not ('influx_host' and 'influx_db') in config['state']:
        logger.info('no influx')
        return

    host = config['state']['influx_host']
    db = config['state']['influx_db']

    url = urllib.parse.urlunsplit(('http', host, '/write', f'db={db}', ''))

    hostname = socket.gethostname()

    while True:
        state = influxdb_state.get()

        data = '\n'.join(
                [f'input_multipliers,box={hostname},ch={ch} multiplier={mult}'
                 for ch, mult in state['multipliers']['input'].items()] +
                [f'output_multipliers,box={hostname},bus={bus} multiplier={mult}'
                 for bus, mult in state['multipliers']['output'].items()] +
                [f'mutes,box={hostname},ch={ch},bus={bus} muted={muted}'
                 for ch, kvp in state['mutes'].items() for bus, muted in kvp.items()]
                )

        requests.post(url, data=data.encode())
