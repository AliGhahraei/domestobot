#!/usr/bin/env python3
from doit_tools import (config, task_compile, task_sort_imports,  # noqa: F401
                        task_sync)

config.main_requirements_source = 'pyproject.toml'
config.extra_dependencies = {
    'linting_requirements.txt': [],
    'test_requirements.txt': [config.main_requirements_file],
    'typing_requirements.txt': [config.main_requirements_file],
    'toolchain_requirements.txt': [config.main_requirements_file],
}
