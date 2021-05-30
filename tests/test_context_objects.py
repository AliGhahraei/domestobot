#!/usr/bin/env python3
from contextlib import contextmanager
from inspect import getmembers, isfunction
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterator

from pytest import fixture, raises
from tomlkit import document, dumps

from domestobot import routines
from domestobot.context_objects import AppObject, Config


@fixture
def default_config_object(tmp_path: Path) -> AppObject:
    return AppObject(tmp_path / 'non_existent_file')


@fixture
def test_path(tmp_path: Path) -> Path:
    return tmp_path / 'file.toml'


@fixture
def test_path_object(test_path: Path) -> AppObject:
    return AppObject(test_path)


@contextmanager
def invalid_config(message: str) -> Iterator[None]:
    with raises(SystemExit,
                match=f'Error while parsing config file: {message}'):
        yield


class TestAppObject:
    class TestRun:
        @staticmethod
        def test_run_command_executes_command(
                default_config_object: AppObject,
        ) -> None:
            output = default_config_object.run('echo', 'hello',
                                               capture_output=True)
            assert 'hello' in output.stdout.decode('utf-8')

        @staticmethod
        def test_run_command_raises_exception_after_error(
                default_config_object: AppObject,
        ) -> None:
            with raises(CalledProcessError,
                        match='Command .* returned non-zero exit status 1.'):
                default_config_object.run('pwd', '--unknown-option')

    @staticmethod
    def test_object_has_routines_as_attributes(
            default_config_object: AppObject,
    ) -> None:
        for routine_name, _ in getmembers(routines, isfunction):
            assert hasattr(default_config_object, routine_name)

    class TestConfig:
        @staticmethod
        def test_config_returns_default_instance_if_file_is_missing(
                default_config_object: AppObject,
        ) -> None:
            assert default_config_object.config == Config()

        @staticmethod
        def test_config_returns_custom_instance_if_file_is_present(
            test_path: Path, test_path_object: AppObject,
        ) -> None:
            doc = document()
            doc['repos'] = ['~/repo1']
            with open(test_path, 'w') as f:
                f.write(dumps(doc))
            assert (test_path_object.config
                    == Config(repos=[Path.home() / 'repo1']))

        @staticmethod
        def test_config_access_shows_message_for_invalid_config_file_format(
            test_path: Path, test_path_object: AppObject,
        ) -> None:
            with open(test_path, 'w') as f:
                f.write('invalid toml')
            with invalid_config('Invalid key "invalid toml" at line 1'
                                ' col 12'):
                getattr(test_path_object, 'config')

        @staticmethod
        def test_config_access_shows_message_for_invalid_config_structure(
            test_path: Path, test_path_object: AppObject,
        ) -> None:
            doc = document()
            doc['repos'] = 1
            with open(test_path, 'w') as f:
                f.write(dumps(doc))
            with invalid_config('expected str, bytes or os.PathLike object,'
                                ' not int'):
                getattr(test_path_object, 'config')
