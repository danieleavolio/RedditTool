import httpx
import pytest
from payloads import ok, ratelimit_headers
from typer.testing import CliRunner

from reddit_analyzer import config
from reddit_analyzer.cli.main import app
from reddit_analyzer.sources.auth import REVOKE_URL
from reddit_analyzer.sources.oauth import BASE_URL

runner = CliRunner()
TOKENS = {"access_token": "ACCESS", "refresh_token": "REFRESH-TOKEN", "expires_in": 3600}


@pytest.fixture
def login_env(mock_reddit, monkeypatch):
    monkeypatch.setattr("reddit_analyzer.cli.auth.webbrowser.open", lambda url: True)
    monkeypatch.setattr("reddit_analyzer.cli.auth.wait_for_code", lambda *a, **k: "CODE")
    mock_reddit.token.mock(return_value=httpx.Response(200, json=TOKENS))
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(return_value=ok({"name": "bob"}))
    return mock_reddit


def test_login_stores_credentials_without_echoing_secrets(login_env, keyring_store):
    result = runner.invoke(app, ["auth", "login", "--client-id", "cid"], input="TOP-SECRET\n")

    assert result.exit_code == 0, result.output
    assert "Logged in as u/bob" in result.output
    assert "TOP-SECRET" not in result.output and "REFRESH-TOKEN" not in result.output
    assert keyring_store == {
        "client_secret": "TOP-SECRET",
        "refresh_token": "REFRESH-TOKEN",
        "username": "bob",
    }
    saved = config.load_settings()
    assert saved.reddit.client_id == "cid"  # persisted to config.toml, not just given as an option
    assert "TOP-SECRET" not in config.config_file_path().read_text()


def test_login_rejected_stores_nothing(login_env, keyring_store):
    login_env.token.mock(return_value=httpx.Response(400, json={"error": "invalid_grant"}))
    result = runner.invoke(app, ["auth", "login", "--client-id", "cid"], input="s\n")
    assert result.exit_code == 1
    assert "rejected" in result.output
    assert keyring_store == {} and not config.config_file_path().exists()


def test_test_command_ok(mock_reddit, keyring_store, monkeypatch):
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    keyring_store.update(client_secret="sec", refresh_token="rt", username="bob")
    mock_reddit.get(f"{BASE_URL}/api/v1/me").mock(
        return_value=ok({"name": "bob"}, **ratelimit_headers(remaining=95, used=5, reset=20))
    )
    result = runner.invoke(app, ["auth", "test"])
    assert result.exit_code == 0, result.output
    assert "OK: logged in as u/bob" in result.output
    assert "95 requests left" in result.output


def test_test_command_without_credentials_points_to_guide():
    result = runner.invoke(app, ["auth", "test"])
    assert result.exit_code == 1
    assert "reddit-credentials.md" in result.output


def test_logout_revokes_and_clears(mock_reddit, keyring_store, monkeypatch):
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    keyring_store.update(client_secret="sec", refresh_token="rt", username="bob")
    revoke = mock_reddit.post(REVOKE_URL).mock(return_value=httpx.Response(204))
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0, result.output
    assert revoke.call_count == 1
    assert keyring_store == {}


def test_logout_works_when_not_logged_in(keyring_store):
    result = runner.invoke(app, ["auth", "logout"])
    assert result.exit_code == 0
    assert keyring_store == {}
