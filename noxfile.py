#!/usr/bin/env python3
from os.path import join

import nox


def reqs(requirements_file):
    return join('requirements', requirements_file)


def install_package(session):
    session.install('-r', reqs('requirements.txt'))
    session.install('.')


@nox.session
def typing(session):
    install_package(session)
    session.install('-r', reqs('typing_requirements.txt'))
    session.run('mypy', 'domestobot')
