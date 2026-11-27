import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """No test may read the real user config or RPA_* variables."""
    for name in [k for k in os.environ if k.startswith("RPA_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("RPA_CONFIG_FILE", str(tmp_path / "config.toml"))
    monkeypatch.setattr("reddit_analyzer.config._keyring_get", lambda key: None)


@pytest.fixture
def load_fixture():
    def _load(name: str):
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    return _load
