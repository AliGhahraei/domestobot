#!/usr/bin/env python3
import os
from glob import glob
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple, Union

from doit import get_var
from doit.action import CmdAction
from doit.tools import result_dep

MAIN_REQUIREMENTS_SOURCE = 'setup.cfg'
MAIN_REQUIREMENTS_FILE = 'requirements.txt'
EXTRA_DEPENDENCIES: Dict[str, List[str]] = {
    'linting_requirements.txt': [],
    'test_requirements.txt': [MAIN_REQUIREMENTS_FILE],
    'typing_requirements.txt': [MAIN_REQUIREMENTS_FILE],
}


def task_sync() -> Dict[str, Any]:
    """Install all necessary requirements in current environment.

    Easiest way to get a working development environment.
    Compile requirements files if not up-to-date and install them using
    pip-sync, then run pip install -e .
    """
    return {
        'actions': ['pip-sync requirements/*.txt', 'pip install -e .'],
        'uptodate': [result_dep('compile')],
    }


def task_sort_imports() -> Iterator[Dict[str, Any]]:
    """Sort import statements in the project's python files."""
    for filepath in glob('**/*.py', recursive=True):
        yield {
            'name': filepath,
            'file_dep': [filepath],
            'actions': ['isort %(dependencies)s'],
        }


def task_compile() -> Iterator[Dict[str, Any]]:
    """Add or update requirements using *.in files as input.

    Run pip-compile to detect changes in source files and add them to *.txt
    files. This will not upgrade versions if it is not necessary, but passing
    upgrade=True will upgrade all dependencies.
    """
    upgrade = get_var('upgrade', False)
    extra_args = '--upgrade' if upgrade else ''
    env = {**os.environ, 'CUSTOM_COMPILE_COMMAND': 'doit compile'}

    for target, deps in generate_requirements():
        command = (f'pip-compile --allow-unsafe --generate-hashes {deps[0]} '
                   f'--output-file {target} {extra_args}')
        yield {
            'name': target,
            'file_dep': deps,
            'targets': [target],
            'actions': [CmdAction(command, env=env)],
            'uptodate': [not upgrade]
        }


def generate_requirements() -> Iterator[Tuple[Path, List[Union[Path, str]]]]:
    requirements_path = Path('requirements')
    main_requirements_path = requirements_path / MAIN_REQUIREMENTS_FILE
    yield main_requirements_path, [MAIN_REQUIREMENTS_SOURCE]

    for target, extra_deps in EXTRA_DEPENDENCIES.items():
        dep_path = requirements_path / f'{Path(target).stem}.in'
        extra_deps_paths = [requirements_path / dep for dep in extra_deps]
        yield requirements_path / target, [dep_path, *extra_deps_paths]
