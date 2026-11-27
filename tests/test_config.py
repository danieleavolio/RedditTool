from pathlib import Path

import pytest

from reddit_analyzer import config
from reddit_analyzer.config import (
    MissingCredentialsError,
    build_user_agent,
    get_credentials,
    load_settings,
)


def test_defaults():
    s = load_settings()
    assert s.reddit.redirect_uri == "http://localhost:8080"
    assert s.reddit.client_id == ""
    assert s.collect.comments_depth == 2
    assert s.collect.morechildren_cap == 20
    assert s.data_dir.name == "reddit-post-analyzer"
    assert s.db_path == s.data_dir / "reddit.db"


def test_toml_overrides_defaults(tmp_path, monkeypatch):
    cfg = tmp_path / "custom.toml"
    cfg.write_text(
        '[reddit]\nclient_id = "from_toml"\n[collect]\nmax_retries = 9\n'
        f'[paths]\ndata_dir = "{(tmp_path / "data").as_posix()}"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("RPA_CONFIG_FILE", str(cfg))
    s = load_settings()
    assert s.reddit.client_id == "from_toml"
    assert s.reddit.redirect_uri == "http://localhost:8080"  # untouched default survives
    assert s.collect.max_retries == 9
    assert s.data_dir == tmp_path / "data"
    assert s.db_path == tmp_path / "data" / "reddit.db"


def test_env_beats_toml(tmp_path, monkeypatch):
    cfg = tmp_path / "custom.toml"
    cfg.write_text('[reddit]\nclient_id = "from_toml"\nredirect_uri = "http://localhost:9999"\n')
    monkeypatch.setenv("RPA_CONFIG_FILE", str(cfg))
    monkeypatch.setenv("RPA_CLIENT_ID", "from_env")  # flat shorthand
    monkeypatch.setenv("RPA_COLLECT__MAX_RETRIES", "7")  # nested form
    s = load_settings()
    assert s.reddit.client_id == "from_env"
    assert s.reddit.redirect_uri == "http://localhost:9999"  # merged, not replaced
    assert s.collect.max_retries == 7


def test_flat_data_dir_env(tmp_path, monkeypatch):
    monkeypatch.setenv("RPA_DATA_DIR", str(tmp_path / "d"))
    assert load_settings().data_dir == Path(tmp_path / "d")


def test_unknown_toml_key_rejected(tmp_path, monkeypatch):
    cfg = tmp_path / "bad.toml"
    cfg.write_text('[reddit]\nclient_secret = "oops"\n')
    monkeypatch.setenv("RPA_CONFIG_FILE", str(cfg))
    with pytest.raises(ValueError):
        load_settings()


def test_missing_credentials_message():
    with pytest.raises(MissingCredentialsError, match="reddit-credentials.md"):
        get_credentials()


def test_credentials_from_env(monkeypatch):
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    monkeypatch.setenv("RPA_CLIENT_SECRET", "s3cret-value")
    monkeypatch.setenv("RPA_REFRESH_TOKEN", "r3fresh-value")
    creds = get_credentials()
    assert creds.client_id == "cid"
    assert creds.client_secret.get_secret_value() == "s3cret-value"
    assert creds.refresh_token.get_secret_value() == "r3fresh-value"


def test_secrets_never_in_repr(monkeypatch):
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    monkeypatch.setenv("RPA_CLIENT_SECRET", "s3cret-value")
    monkeypatch.setenv("RPA_REFRESH_TOKEN", "r3fresh-value")
    creds = get_credentials()
    text = repr(creds) + str(creds) + creds.model_dump_json() + repr(load_settings())
    assert "s3cret-value" not in text
    assert "r3fresh-value" not in text


def test_credentials_fall_back_to_keyring(monkeypatch):
    store = {"client_secret": "kr-secret", "refresh_token": "kr-refresh", "username": "bob"}
    monkeypatch.setattr(config, "_keyring_get", store.get)
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    creds = get_credentials()
    assert creds.client_secret.get_secret_value() == "kr-secret"
    assert creds.refresh_token.get_secret_value() == "kr-refresh"
    assert creds.username == "bob"


def test_refresh_token_optional(monkeypatch):
    monkeypatch.setenv("RPA_CLIENT_ID", "cid")
    monkeypatch.setenv("RPA_CLIENT_SECRET", "x")
    assert get_credentials().refresh_token is None


def test_user_agent_format():
    ua = build_user_agent("bob")
    assert ua.startswith("python:reddit-post-analyzer:")
    assert ua.endswith("(by /u/bob)")
    assert "/u/unknown" in build_user_agent(None)
