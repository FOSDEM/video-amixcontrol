#!/usr/bin/env python3

import uvicorn
import tomllib
from mixerapi.fosdemapi import app
from mixerapi.config import get_config


def main():
    config = get_config()

    server_conf = uvicorn.Config("mixerapi.fosdemapi:app", host=config['host']['listen'], port=config['host']['port'])
    server = uvicorn.Server(server_conf)
    server.run()


if __name__ == "__main__":
    main()
