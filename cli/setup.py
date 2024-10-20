#!/usr/bin/env python3

import os
import re

from setuptools import setup

tag = os.environ.get("CIRCLE_TAG")
build_no = os.environ.get("CIRCLE_BUILD_NUM")

version = ""

if tag and re.match(r"^v[0-9].*", tag):
    version = tag[1:]
else:
    version = "0.0." + (build_no if build_no else "1")

setup(
        version = version
)
