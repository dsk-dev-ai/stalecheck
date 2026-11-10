import pytest


@pytest.fixture(autouse=True)
def isolated_env(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    monkeypatch.setenv("TAVILY_API_KEY", "")
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))

    from stalecheck_api.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
