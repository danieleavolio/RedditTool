from typer.testing import CliRunner

from reddit_analyzer import __version__
from reddit_analyzer.cli.main import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output.strip() == f"rpa {__version__}"


def test_gui_command_explains_the_missing_extra(monkeypatch):
    monkeypatch.setitem(__import__("sys").modules, "streamlit", None)  # makes the import fail
    result = runner.invoke(app, ["gui"])
    assert result.exit_code == 1
    assert "reddit-post-analyzer[gui]" in result.output
