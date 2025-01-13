#!/usr/bin/env python3

import os
import sys
import socket

from fastapi import FastAPI

from fosdemosc import OSCController
from fosdemosc import helpers
from fosdemosc import VUMeter

from typing import List, Any

from mixerapi.config import get_config


config = get_config()

app = FastAPI()

osc: OSCController
if 'device' in config['conn'] and config['conn']['device']:
    osc = OSCController(config['conn']['device'])
else:
    osc = OSCController(config['conn']['host'], config['conn']['port'], 'udp')

@app.get("/")
async def root():
#async def root() -> List[List[float]]:
    return osc.get_state()

@app.get("/matrix")
async def matrix() -> List[List[float]]:
    return osc.get_matrix()

@app.get("/matrix/raw")
async def raw_matrix() -> List[List[float]]:
    pass

@app.get("/vu/input")
async def input_vu() -> dict[str, VUMeter]:
    return osc.get_channel_vu_meters()

@app.get("/vu/output")
async def output_vu() -> dict[str, VUMeter]:
    return osc.get_bus_vu_meters()

@app.get("/multipliers/input")
async def input_multipliers() -> dict[str, float]:
    return osc.get_channel_multipliers()

@app.get("/multipliers/output")
async def output_multipliers() -> dict[str, float]:
    return osc.get_bus_multipliers()

@app.get("/mutes")
async def mutes():
    return osc.get_mutes()


@app.get("/multipliers")
async def multipliers() -> dict[str, dict[str, float]]:
    return {'input': osc.get_channel_multipliers(), 'output': osc.get_bus_multipliers() }

@app.get("/vu")
async def vu() -> dict[str, dict[str, VUMeter]]:
    return {'input': osc.get_channel_vu_meters(), 'output': osc.get_bus_vu_meters() }

@app.get("/info")
async def info() -> dict[str, Any]:
    return {
            'host': socket.gethostname(),
            'device': osc.device,
            'inputs': osc.inputs,
            'outputs': osc.outputs,
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
