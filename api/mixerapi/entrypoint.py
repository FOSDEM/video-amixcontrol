#!/usr/bin/env python3

import multiprocessing
import os

import uvicorn
import tomllib

import logging

from mixerapi.fosdemapi import define_webapp
from mixerapi.config import get_config
from mixerapi.helpers import StateEvent

from . import levels, state

def run_web(config, fastapi):
    uvicorn.run(fastapi,
            host=config['host']['listen'],
            port=config['host']['port'],
            proxy_headers=True,
            forwarded_allow_ips='*',
    )

def main():
    config = get_config()

    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter('%(name)s :: %(levelname)s :: %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[ch])

    log = logging.getLogger('CTRL')

    manager = multiprocessing.Manager()

    levels_web = StateEvent(manager.Event(), manager.dict())
    state_web = StateEvent(manager.Event(), manager.dict())

    fastapi = define_webapp(levels_web, state_web)

    levels_processes = levels.start(config, levels_web)
    state_processes = state.start(config, state_web)

    web_process = multiprocessing.Process(target=run_web, args=(config, fastapi,))

    levels_processes[0].start()
    levels_processes[1].start()
    state_processes[0].start()
    state_processes[1].start()
    web_process.start()

    log.info(f'Controller PID {os.getpid()}')
    log.info(f'Levels Poller PID {levels_processes[0].pid}')
    log.info(f'Levels Pusher PID {levels_processes[1].pid}')
    log.info(f'State Poller PID {state_processes[0].pid}')
    log.info(f'State Pusher PID {state_processes[1].pid}')
    log.info(f'Web PID {web_process.pid}')

    levels_processes[0].join()
    levels_processes[1].join()
    state_processes[0].join()
    state_processes[1].join()
    web_process.join()


if __name__ == "__main__":
    main()
