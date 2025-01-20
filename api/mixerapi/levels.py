from fosdemosc import OSCController

import asyncio
import aiohttp
import urllib.parse

import socket

import math
import itertools
import dataclasses

def shanod(x):
    return {k: dataclasses.asdict(v) for k, v in x.items()}

def get_levels(osc: OSCController):
    return ({'input': shanod(osc.get_channel_vu_meters()), 'output': shanod(osc.get_bus_vu_meters()) })

web_event = asyncio.Event()
influxdb_event = asyncio.Event()

web_levels = None
influxdb_levels = None

async def poll_levels(osc: OSCController, config):
    global web_levels, web_event
    global influxdb_levels, influxdb_event

    int_web = config['levels']['interval_web']
    int_influxdb = config['levels']['interval_influxdb']

    poll_base = math.gcd(int_web, int_influxdb)
    poll_count = math.lcm(int_web, int_influxdb)

    mult_web = poll_base / int_web
    mult_influxdb = poll_base / int_influxdb

    # like `while True`, but counts the cycle, and keeps it from overflowing
    for i in itertools.cycle(range(poll_count)):
        await asyncio.sleep(poll_base / 1000)
        levels = get_levels(osc)
        if i % mult_web == 0 and not web_event.is_set():
            web_levels = dict(levels)
            web_event.set()
        if i % mult_influxdb == 0 and not influxdb_event.is_set():
            influxdb_levels = dict(levels)
            influxdb_event.set()

async def web_get_levels():
    global web_levels, web_event
    await web_event.wait()
    web_event.clear()
    return web_levels

async def influxdb_get_levels():
    global influxdb_levels, influxdb_event
    await influxdb_event.wait()
    influxdb_event.clear()
    return influxdb_levels

async def push_influxdb(config):
    if not 'influxdb' in config:
        print('no influx')
        return
    if not ('host' in config['influxdb'] and 'db' in config['influxdb']):
        print('no host')
        return

    host = config['influxdb']['host']
    db = config['influxdb']['db']

    url = urllib.parse.urlunsplit(('http', host, '/write', f'db={db}', ''))

    hostname = socket.gethostname()

    while True:
        levels = await influxdb_get_levels()

        data = '\n'.join(
                [f'input_levels,box={hostname},ch={ch} rms={vu["rms"]},peak={vu["peak"]},smooth={vu["smooth"]}' 
                 for ch, vu in levels['input'].items()] +
                [f'output_levels,box={hostname},bus={bus} rms={vu["rms"]},peak={vu["peak"]},smooth={vu["smooth"]}' 
                 for bus, vu in levels['output'].items()])

        async with aiohttp.ClientSession() as session:
            await session.post(url, data=data.encode())
