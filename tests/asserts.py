from pytest import CaptureFixture


def readout(capsys: CaptureFixture[str]) -> str:
    return capsys.readouterr().out


def assert_stdout(message: str, capsys: CaptureFixture[str]) -> None:
    assert message in readout(capsys)


def assert_no_stdout(capsys: CaptureFixture[str]) -> None:
    assert not readout(capsys)
