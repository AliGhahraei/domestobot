from domestobot._core import DefaultRunner


class TestDefaultRunner:
    @staticmethod
    def test_runner_executes_command() -> None:
        result = DefaultRunner()("echo", "hi", capture_output=True)
        assert "hi" in result.stdout.decode()
