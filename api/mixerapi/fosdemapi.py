#!/usr/bin/env python3

import os
import sys
import socket
import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket, WebSocketDisconnect

import dataclasses

from fosdemosc import OSCController, parse_bus, parse_channel, parse_level
from fosdemosc import VUMeter

from typing import List, Any

from mixerapi.config import get_config

from . import levels

config = get_config()

app = FastAPI()

logger = logging.getLogger(__name__)

osc: OSCController

def connect_osc():
    global osc
    logger.info(f"Connecting to serial {config['conn']}")
    if 'device' in config['conn'] and config['conn']['device']:
        osc = OSCController(config['conn']['device'])
        logger.info(f"Created serial connection to {config['conn']['device']}")
    else:
        osc = OSCController(config['conn']['host'], config['conn']['port'], mode='udp')
        logger.info(f"Connected to UDP {config['conn']['host']}:{config['conn']['port']}")

connect_osc()

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(levels.poll_levels(osc, config))
    asyncio.create_task(levels.push_influxdb(config))
    logger.info("Started background tasks")


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

@app.get("/vu")
async def vu() -> dict[str, dict[str, VUMeter]]:
    return {'input': osc.get_channel_vu_meters(), 'output': osc.get_bus_vu_meters() }

@app.websocket("/vu/ws")
async def vu_ws(websocket: WebSocket):
    try:
        await websocket.accept()
        while True:
            await websocket.send_json(await levels.web_get_levels())
    except WebSocketDisconnect as e:
        return

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


@app.get("/gain/{channel}/{bus}")
async def get_gain(channel: str, bus: str) -> float:
    channel = parse_channel(osc, channel)
    bus = parse_bus(osc, bus)
    return osc.get_gain(channel, bus)


@app.post("/gain/{channel}/{bus}")
@app.put("/gain/{channel}/{bus}")
@app.get("/gain/{channel}/{bus}/{level}")
async def set_gain(channel: str, bus: str, level: str) -> None:
    channel = parse_channel(osc, channel)
    bus = parse_bus(osc, bus)
    level = parse_level(osc, level)

    osc.set_gain(channel, bus, level)
