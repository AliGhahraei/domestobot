#!/usr/bin/env python3
import os
from glob import glob
from pathlib import Path

from doit import get_var
from doit.action import CmdAction
from doit.tools import result_dep

MAIN_REQUIREMENTS_SOURCE = 'pyproject.toml'


def task_sort_imports():
    """Sort import statements in the project's python files """
    for filepath in glob('**/*.py', recursive=True):
        yield {
            'name': filepath,
            'file_dep': [filepath],
            'actions': ['isort %(dependencies)s'],
        }


def task_compile():
    """Run pip-compile for the requirements files"""
    upgrade = get_var('upgrade', False)
    extra_args = ' --upgrade' if upgrade else ''

    def action(dependencies, targets):
        return (f'pip-compile --allow-unsafe --generate-hashes'
                f' {dependencies[0]} --output-file {targets[0]} {extra_args}')

    env = {**os.environ.copy(), 'CUSTOM_COMPILE_COMMAND': 'doit compile'}
    cmd_action = CmdAction(action, env=env)
    for target, deps in generate_requirements():
        yield {
            'name': target,
            'file_dep': deps,
            'targets': [target],
            'actions': [cmd_action],
            'uptodate': [not upgrade]
        }


def generate_requirements():
    requirements_path = Path('requirements')
    main_target = 'requirements.txt'
    extra_requirements = {
        'linting_requirements.txt': [],
        'test_requirements.txt': [main_target],
        'typing_requirements.txt': [main_target],
    }

    yield requirements_path / main_target, [MAIN_REQUIREMENTS_SOURCE]
    for target, extra_deps in extra_requirements.items():
        dep_path = requirements_path / f'{Path(target).stem}.in'
        extra_deps_paths = [requirements_path / dep for dep in extra_deps]
        yield requirements_path / target, [dep_path, *extra_deps_paths]


def task_sync():
    """Run pip-sync for the requirements files and then pip install -e ."""
    return {
        'actions': ['pip-sync requirements/*.txt', 'pip install -e .'],
        'uptodate': [result_dep('compile')],
    }
