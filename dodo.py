#!/usr/bin/env python3
from doit_tools import config, task_compile, task_sort_imports, task_sync

config.main_requirements_source = 'pyproject.toml'
config.extra_dependencies = {
    'linting_requirements.txt': [],
    'packaging_requirements.txt': [],
    'test_requirements.txt': [config.main_requirements_file],
    'typing_requirements.txt': [config.main_requirements_file],
}
