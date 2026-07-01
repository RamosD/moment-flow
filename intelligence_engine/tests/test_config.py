import pytest

from app.core.config import Settings
from app.core.errors import ConfigError


def test_settings_default_values_when_env_is_empty() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.service_name == "intelligence_engine"
    assert settings.service_version == "0.1.0"
    assert settings.log_level == "INFO"
    assert settings.internal_api_token == ""


def test_settings_reads_values_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "shared-secret-for-tests-only")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.log_level == "WARNING"
    assert settings.internal_api_token == "shared-secret-for-tests-only"


def test_settings_rejects_unknown_app_env() -> None:
    try:
        Settings(_env_file=None, app_env="not-a-real-env")
    except Exception as exc:  # pydantic ValidationError
        assert "app_env" in str(exc)
    else:
        raise AssertionError("Expected validation error for invalid app_env")


def test_settings_blocks_boot_when_production_token_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "")

    with pytest.raises(ConfigError) as exc_info:
        Settings(_env_file=None)

    assert exc_info.value.code == "config_error"
    assert "INTERNAL_API_TOKEN" in exc_info.value.message


def test_settings_blocks_boot_when_production_token_is_whitespace_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "   ")

    with pytest.raises(ConfigError):
        Settings(_env_file=None)


def test_settings_strips_whitespace_from_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "  padded-token  ")

    settings = Settings(_env_file=None)

    assert settings.internal_api_token == "padded-token"


def test_settings_allows_empty_token_outside_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("INTERNAL_API_TOKEN", "")

    settings = Settings(_env_file=None)

    assert settings.internal_api_token == ""
