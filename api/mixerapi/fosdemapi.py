#!/usr/bin/env python3

import os
import sys
import socket

from fastapi import FastAPI

from fosdemosc import OSCController
from fosdemosc import helpers

from typing import List

from mixerapi.config import get_config


config = get_config()

app = FastAPI()
osc = OSCController(config['conn']['device'])

@app.get("/")
async def root() -> List[List[float]]:
    return osc.get_matrix()

@app.get("/info")
async def info() -> dict[str, str]:
    return {
            'host': socket.gethostname(),
            'device': osc.device,
    }


@app.get("/channels")
async def get_channels() -> List[str]:
    return osc.inputs


@app.get("/buses")
async def get_buses() -> List[str]:
    return osc.outputs


@app.get("/{channel}/{bus}")
async def get_gain(channel: str, bus: str) -> float:
    channel = helpers.parse_channel(osc, channel)
    bus = helpers.parse_bus(osc, bus)
    return osc.get_gain(channel, bus)


@app.post("/{channel}/{bus}")
@app.put("/{channel}/{bus}")
@app.get("/{channel}/{bus}/{level}")
async def set_gain(channel: str, bus: str, level: str) -> None:
    channel = helpers.parse_channel(osc, channel)
    bus = helpers.parse_bus(osc, bus)
    level = helpers.parse_level(osc, level)

    osc.set_gain(channel, bus, level)
