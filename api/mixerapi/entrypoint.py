#!/usr/bin/env python3

import uvicorn
import tomllib

import logging

from mixerapi.fosdemapi import app
from mixerapi.config import get_config


def main():
    config = get_config()


    logging.basicConfig(level=logging.INFO)

    uvicorn.run("mixerapi.fosdemapi:app",
            host=config['host']['listen'],
            port=config['host']['port'],
            proxy_headers=True,
            forwarded_allow_ips='*',
    )


if __name__ == "__main__":
    main()
