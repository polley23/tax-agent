import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="TAX_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment mode
    env: str = "development"
    debug: bool = True

    # Desktop mode: when True, writes a port file for Tauri supervisor
    desktop_mode: bool = False

    # Data directory — stores SQLite DB, uploads, port file
    tax_agent_data_dir: Path = Path.user_data_path("tax-agent") if os.name == "nt" else Path.home() / ".local" / "share" / "tax-agent"  # noqa: E501

    # Server binding — loopback only for security
    host: str = "127.0.0.1"
    port: int = 9090

    # Database (SQLite file lives inside data dir)
    database_url: str = "sqlite+aiosqlite:///tax_agent.db"

    # Optional basic auth for local API
    app_password: str = ""

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # Ollama
    ollama_host: str = "127.0.0.1:11434"
    ollama_model: str = "llama3.1:8b"

    # Logging
    log_level: str = "DEBUG"
    log_json: bool = True

    # Upload limits (bytes)
    max_upload_size: int = 10 * 1024 * 1024  # 10 MB

    # CORS — allow Tauri + loopback only
    allowed_origins: list[str] = [
        "http://localhost",
        "http://127.0.0.1",
        "tauri://localhost",
    ]

    @property
    def db_path_str(self) -> str:
        """Full path to the SQLite database inside the data directory."""
        db_file = self.tax_agent_data_dir / "tax_agent.db"
        return f"sqlite+aiosqlite:///{db_file}"

    @property
    def uploads_path(self) -> Path:
        return self.tax_agent_data_dir / "uploads"

    def write_port_file(self) -> None:
        """Write port number to data dir for Tauri supervisor."""
        if self.desktop_mode:
            port_file = self.tax_agent_data_dir / "api_port.txt"
            port_file.write_text(str(self.port))

    def ensure_data_dirs(self) -> None:
        """Create required data directories if they don't exist."""
        self.tax_agent_data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_path.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
