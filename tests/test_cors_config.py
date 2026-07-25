import re

from src.core.config import Settings


def test_production_cors_excludes_localhost() -> None:
    settings = Settings(
        _env_file=None,
        app_env="production",
        cors_origins="https://skygate.vercel.app",
    )

    assert settings.allowed_cors_origins == [
        "https://gatesky.com.br",
        "https://www.gatesky.com.br",
        "https://skygate.vercel.app",
    ]
    assert all("localhost" not in origin for origin in settings.allowed_cors_origins)
    assert all("127.0.0.1" not in origin for origin in settings.allowed_cors_origins)


def test_development_cors_includes_localhost() -> None:
    settings = Settings(_env_file=None, app_env="development", cors_origins="")

    expected_origins = {
        "https://gatesky.com.br",
        "https://www.gatesky.com.br",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "http://localhost:5173",
    }

    assert expected_origins.issubset(settings.allowed_cors_origins)


def test_vercel_preview_regex_only_accepts_https_vercel_subdomains() -> None:
    settings = Settings(_env_file=None)

    assert re.fullmatch(settings.cors_origin_regex, "https://skygate-git-main-team.vercel.app")
    assert not re.fullmatch(settings.cors_origin_regex, "http://skygate.vercel.app")
    assert not re.fullmatch(settings.cors_origin_regex, "https://vercel.app.evil.example")
