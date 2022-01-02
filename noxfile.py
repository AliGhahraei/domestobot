#!/usr/bin/env python3
from glob import glob
from os.path import join

import nox

PYTHON_FILES = 'domestobot', 'tests', *glob('*.py')


def install_reqs(requirements_file: str, session: nox.Session) -> None:
    session.install('-r', join('requirements', requirements_file))


def install_package(session: nox.Session) -> None:
    install_reqs('requirements.txt', session)
    session.install('.')


def install_test_packages(session: nox.Session) -> None:
    install_reqs('test_requirements.txt', session)


@nox.session
def tests(session: nox.Session) -> None:
    install_package(session)
    install_test_packages(session)
    session.run('coverage', 'run', '-m', 'pytest')
    session.run('coverage', 'report')


@nox.session
def typing(session: nox.Session) -> None:
    install_package(session)
    install_test_packages(session)
    install_reqs('typing_requirements.txt', session)
    install_reqs('toolchain_requirements.txt', session)
    session.run('mypy')


@nox.session
def linting(session: nox.Session) -> None:
    install_reqs('linting_requirements.txt', session)
    session.run('isort', '--check-only', *PYTHON_FILES)
    session.run('flake8', *PYTHON_FILES)
