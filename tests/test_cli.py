from typer.testing import CliRunner

from reddit_analyzer import __version__
from reddit_analyzer.cli.main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"rpa {__version__}"
