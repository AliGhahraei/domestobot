#!/usr/bin/env python3
from os.path import join

import nox


def install_reqs(requirements_file, session):
    session.install('-r', join('requirements', requirements_file))


def install_package(session):
    install_reqs('requirements.txt', session)
    session.install('.')


def install_test_packages(session):
    install_reqs('test_requirements.txt', session)


@nox.session
def tests(session):
    install_package(session)
    install_test_packages(session)
    session.run('coverage', 'run', '-m', 'pytest')
    session.run('coverage', 'report')


@nox.session
def typing(session):
    install_package(session)
    install_test_packages(session)
    install_reqs('typing_requirements.txt', session)
    session.run('mypy')
