#!/usr/bin/env python3

import os
import sys
import socket
import asyncio
import logging
import re

from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket, WebSocketDisconnect

import dataclasses

from fosdemosc import OSCController, parse_bus, parse_channel, parse_level
from fosdemosc import VUMeter

from typing import List, Any
from collections import defaultdict

from mixerapi.config import get_config

from . import helpers


def define_webapp(levels, state):

    config = get_config()

    app = FastAPI()

    logger = logging.getLogger("mixerapi")

    osc = helpers.connect_osc(config)

    @app.get("/")
    @app.get("/state")
    async def get_state():
        return osc.get_state()


    @app.websocket("/state/ws")
    async def state_ws(websocket: WebSocket):
        try:
            await websocket.accept()
            await websocket.send_json(osc.get_state())
            while True:
                await websocket.send_json(await asyncio.get_event_loop().run_in_executor(None, state.get_copy))
        except WebSocketDisconnect as e:
            return

    @app.websocket("/vu/ws")
    async def vu_ws(websocket: WebSocket):
        try:
            await websocket.accept()
            initial_levels = helpers.get_all_levels(osc)
            if initial_levels:
                await websocket.send_json(initial_levels)
            while True:
                await websocket.send_json(await asyncio.get_event_loop().run_in_executor(None, levels.get_copy))
        except WebSocketDisconnect as e:
            return

    @app.get("/vu/input")
    async def input_vu() -> dict[str, VUMeter]:
        return osc.get_channel_vu_meters()

    @app.get("/vu/output")
    async def output_vu() -> dict[str, VUMeter]:
        return osc.get_bus_vu_meters()

    @app.get("/matrix")
    async def get_matrix() -> List[List[float]]:
        return osc.get_matrix()

    @app.get("/multipliers/input")
    async def input_multipliers() -> dict[str, float]:
        return osc.get_channel_multipliers()

    @app.post("/multipliers/input/{channel}")
    @app.put("/multipliers/input/{channel}")
    @app.get("/multipliers/input/{channel}/{multiplier}")
    async def set_input_multiplier(channel: str, multiplier: float) -> None:
        channel = parse_channel(osc, channel)
        multiplier = float(multiplier)

        osc.set_channel_multiplier(channel, multiplier)
        state.set(lambda x: helpers.merge(x, osc.get_state()))

    @app.get("/multipliers/output")
    async def output_multipliers() -> dict[str, float]:
        return osc.get_bus_multipliers()

    @app.post("/multipliers/output/{bus}")
    @app.put("/multipliers/output/{bus}")
    @app.get("/multipliers/output/{bus}/{multiplier}")
    async def set_output_multiplier(bus: str, multiplier: float) -> None:
        bus = parse_bus(osc, bus)
        multiplier = float(multiplier)

        osc.set_bus_multiplier(bus, multiplier)
        state.set(lambda x: helpers.merge(x, osc.get_state()))

    @app.get("/mutes")
    async def mutes():
        return osc.get_mutes()

    @app.post("/muted/{channel}/{bus}")
    @app.put("/muted/{channel}/{bus}")
    @app.get("/muted/{channel}/{bus}/{mute}")
    async def set_mute(channel: str, bus: str, mute: str):
        channel = parse_channel(osc, channel)
        bus = parse_bus(osc, bus)
        muted = helpers.strtobool(mute)

        osc.set_muted(channel, bus, muted)
        state.set(lambda x: helpers.merge(x, osc.get_state()))


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

        state.set(lambda x: helpers.merge(x, osc.get_state()))

    return app
