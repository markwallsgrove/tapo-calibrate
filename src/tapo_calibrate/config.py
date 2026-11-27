"""Where the camera is and how to log in, read from the environment."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from urllib.parse import quote

ENV_HOST = "TAPO_HOST"
ENV_PASSWORD = "TAPO_PASSWORD"
ENV_RTSP_USER = "TAPO_RTSP_USER"
ENV_RTSP_PASSWORD = "TAPO_RTSP_PASSWORD"
HIDDEN = "***"


class ConfigError(Exception):
    """A setting the tool needs is missing."""


@dataclass(frozen=True)
class Config:
    """The camera's address and logins. The passwords never appear in repr or in scrubbed text."""

    host: str
    password: str = field(repr=False)
    rtsp_user: str = field(repr=False)
    rtsp_password: str = field(repr=False)

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Config":
        """Read every setting, naming all the missing ones at once."""
        names = (ENV_HOST, ENV_PASSWORD, ENV_RTSP_USER, ENV_RTSP_PASSWORD)
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise ConfigError(f"Set {', '.join(missing)} in the environment")
        return cls(env[ENV_HOST], env[ENV_PASSWORD], env[ENV_RTSP_USER], env[ENV_RTSP_PASSWORD])

    @property
    def rtsp_url(self) -> str:
        """The camera's high quality stream, with the camera account in it."""
        login = f"{quote(self.rtsp_user, safe='')}:{quote(self.rtsp_password, safe='')}"
        return f"rtsp://{login}@{self.host}:554/stream1"

    def scrub(self, text: str) -> str:
        """Text with every secret, plain or URL-quoted, replaced by ***."""
        for secret in (self.password, self.rtsp_user, self.rtsp_password):
            text = text.replace(secret, HIDDEN).replace(quote(secret, safe=""), HIDDEN)
        return text
