import os
import tomllib
from functools import lru_cache
import sys
import logging

def get_logger():
    return logging.getLogger()

@lru_cache
def get_config(conffile_locations = ['./mixerapi.conf', '~/mixerapi.conf', '/etc/mixerapi.conf']):
    conffile = next((x for x in conffile_locations if os.access(x, os.R_OK)), None) # get first existing file, or None

    with open(conffile, "rb") as f:
        get_logger().info("Using config file " + os.path.abspath(conffile))
        config = tomllib.load(f)

        return config
