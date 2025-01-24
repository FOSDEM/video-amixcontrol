from fosdemosc import OSCController

import asyncio
import threading
import aiohttp
import urllib.parse

import socket

import math
import itertools
import dataclasses

from . import helpers

import logging

logger = logging.getLogger("state")

statechange_event = asyncio.Event()

state = None

async def setup(config):
    asyncio.create_task(poll_state(config))

async def update_state(new_state):
    global state

    if not new_state:
        return

    state = new_state
    statechange_event.set()

async def poll_state(config):
    osc = helpers.connect_osc(config)
    logger.info(f"Connected to {osc.device}")

    global state

    interval = config['poll']['state']

    while True:
        await asyncio.sleep(interval / 1000)
        try:
            await update_state(osc.get_state())
        except:
            logger.error("Timeout getting info from mixer")

async def wait_for_state():
    global state, statechange_event
    await statechange_event.wait()
    statechange_event.clear()
    return state

def get_web_cached_state():
    return state

async def web_get_state():
    return await wait_for_state()
