"""Configuration for the Rhino MCP client.

Loads Rhino MCP connection settings from environment variables with sensible
defaults. Supports both TCP (host/port) and stdio transport modes.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_bool(name: str, default: bool = False) -> bool:
    """Parse a boolean environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    """Parse a float environment variable."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _env_int(name: str, default: int) -> int:
    """Parse an integer environment variable."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _env_str(name: str, default: str) -> str:
    """Parse a string environment variable."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _default_stdio_command() -> str:
    """Return the path to the installed Rhino MCP router, if present.

    The router ships with the Rhino-MCP-Platform Yak package under the
    user's roaming AppData directory. Falls back to the legacy ``rhinomcp``
    PyPI package for environments where the router isn't installed.
    """
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        router = os.path.join(
            appdata,
            "McNeel", "Rhinoceros", "packages", "8.0",
            "Rhino-MCP-Platform", "0.1.5", "router", "win-x64",
            "rhino-mcp-router.exe",
        )
        if os.path.isfile(router):
            return router
    return "uvx --from rhinomcp==0.4.1.1 rhinomcp"


@dataclass
class RhinoMCPConfig:
    """Connection settings for the Rhino MCP server.

    Attributes:
        host: TCP hostname or IP for the Rhino MCP server.
        port: TCP port for the Rhino MCP server.
        timeout: Default request timeout in seconds.
        use_stdio: When True, use stdio transport instead of TCP.
        stdio_command: Command used to launch the MCP server in stdio mode.
        max_retries: Maximum number of connection/request retries.
        retry_backoff: Base backoff (seconds) between retries (exponential).
        enable_run_command: Whether ``run_command`` is allowed.
        enable_rhinoscript: Whether Rhinoscript execution is allowed.
        enable_csharp: Whether RhinoCommon C# execution is allowed.
    """

    host: str = field(default_factory=lambda: _env_str("RHINO_MCP_HOST", "localhost"))
    port: int = field(default_factory=lambda: _env_int("RHINO_MCP_PORT", 8765))
    timeout: float = field(default_factory=lambda: _env_float("RHINO_MCP_TIMEOUT", 30.0))
    use_stdio: bool = field(default_factory=lambda: _env_bool("RHINO_MCP_USE_STDIO", False))
    stdio_command: str = field(
        default_factory=lambda: _env_str(
            "RHINO_MCP_STDIO_COMMAND", _default_stdio_command()
        )
    )
    max_retries: int = field(default_factory=lambda: _env_int("RHINO_MCP_MAX_RETRIES", 3))
    retry_backoff: float = field(
        default_factory=lambda: _env_float("RHINO_MCP_RETRY_BACKOFF", 1.0)
    )
    enable_run_command: bool = field(
        default_factory=lambda: _env_bool("RHINO_MCP_ENABLE_RUN_COMMAND", True)
    )
    enable_rhinoscript: bool = field(
        default_factory=lambda: _env_bool("RHINO_MCP_ENABLE_RHINOSCRIPT", True)
    )
    enable_csharp: bool = field(
        default_factory=lambda: _env_bool("RHINO_MCP_ENABLE_CSHARP", True)
    )
    use_http: bool = field(
        default_factory=lambda: _env_bool("RHINO_MCP_USE_HTTP", False)
    )
    http_url: str = field(
        default_factory=lambda: _env_str("RHINO_MCP_HTTP_URL", "")
    )

    def __post_init__(self) -> None:
        # Derive http_url from host/port unless explicitly overridden via
        # RHINO_MCP_HTTP_URL or an explicit constructor argument, so that a
        # custom host/port (e.g. in tests) is actually honored over HTTP.
        if not self.http_url:
            self.http_url = f"http://{self.host}:{self.port}"

    @property
    def tcp_address(self) -> str:
        """Return the TCP address in host:port form."""
        return f"{self.host}:{self.port}"

    def validate(self) -> None:
        """Validate configuration values, raising ValueError on bad settings."""
        if not (0 < self.port < 65536):
            raise ValueError(f"RHINO_MCP_PORT must be 1-65535, got {self.port}")
        if self.timeout <= 0:
            raise ValueError(
                f"RHINO_MCP_TIMEOUT must be positive, got {self.timeout}"
            )
        if self.max_retries < 0:
            raise ValueError(
                f"RHINO_MCP_MAX_RETRIES must be >= 0, got {self.max_retries}"
            )
        if self.retry_backoff < 0:
            raise ValueError(
                f"RHINO_MCP_RETRY_BACKOFF must be >= 0, got {self.retry_backoff}"
            )


# Module-level singleton config instance.
config: RhinoMCPConfig = RhinoMCPConfig()


def get_config() -> RhinoMCPConfig:
    """Return the shared RhinoMCPConfig instance."""
    return config


def reload_config() -> RhinoMCPConfig:
    """Re-read environment variables and return a fresh config instance."""
    global config
    config = RhinoMCPConfig()
    config.validate()
    return config
