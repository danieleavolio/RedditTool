import json
import os
from pathlib import Path

import httpx
import pytest
import respx
from pydantic import SecretStr

from reddit_analyzer import config
from reddit_analyzer.config import Credentials, load_settings
from reddit_analyzer.sources.auth import TOKEN_URL
from reddit_analyzer.sources.oauth import RedditClient

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_env(request, monkeypatch, tmp_path):
    """No test may read the real user config, RPA_* variables or the real keyring.

    Tests marked ``live`` are the exception: they use the real environment on purpose.
    """
    if request.node.get_closest_marker("live"):
        return
    for name in [k for k in os.environ if k.startswith("RPA_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("RPA_CONFIG_FILE", str(tmp_path / "config.toml"))


@pytest.fixture(autouse=True)
def keyring_store(request, monkeypatch):
    """In-memory stand-in for the system keyring."""
    store: dict[str, str] = {}
    if not request.node.get_closest_marker("live"):
        monkeypatch.setattr(config, "_keyring_get", store.get)
        monkeypatch.setattr(config, "_keyring_set", store.__setitem__)
        monkeypatch.setattr(config, "_keyring_delete", lambda key: store.pop(key, None))
    return store


@pytest.fixture
def load_fixture():
    def _load(name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def mock_reddit():
    """respx router with a working token endpoint; individual tests add API routes."""
    with respx.mock(assert_all_called=False) as router:
        router.token = router.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200, json={"access_token": "tok", "expires_in": 3600, "token_type": "bearer"}
            )
        )
        yield router


@pytest.fixture
def creds():
    return Credentials(
        client_id="cid",
        client_secret=SecretStr("sec"),
        refresh_token=SecretStr("rt"),
        username="bob",
    )


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def make_client(creds, sleeps):
    def _make(settings=None):
        return RedditClient(creds, settings or load_settings(), sleep=sleeps.append)

    return _make
