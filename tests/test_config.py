import pytest

from tapo_calibrate.config import ENV_HOST, ENV_RTSP_USER, Config, ConfigError

from .conftest import ENV


def test_reads_every_setting() -> None:
    config = Config.from_env(ENV)
    assert config.host == "192.0.2.10"
    assert config.rtsp_url == "rtsp://cam-user:p%40ss%3Aword@192.0.2.10:554/stream1"


def test_names_every_missing_setting() -> None:
    env = {key: value for key, value in ENV.items() if key not in {ENV_HOST, ENV_RTSP_USER}}
    with pytest.raises(ConfigError, match=f"{ENV_HOST}, {ENV_RTSP_USER}"):
        Config.from_env(env)


def test_repr_hides_the_logins() -> None:
    text = repr(Config.from_env(ENV))
    assert "cloud-secret" not in text
    assert "cam-user" not in text
    assert "p@ss:word" not in text


def test_scrub_hides_plain_and_quoted_secrets() -> None:
    config = Config.from_env(ENV)
    text = config.scrub(f"failed {config.rtsp_url} with cloud-secret and p@ss:word")
    assert text == "failed rtsp://***:***@192.0.2.10:554/stream1 with *** and ***"
