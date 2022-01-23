#!/usr/bin/env python3
from nox_tools import config, linting, tests, typing

config.module = 'domestobot'
config.sessions = [linting, tests, typing]
