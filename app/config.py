"""Configuration management using pydantic-settings."""

from pathlib import Path
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API Configuration
    gemini_api_key: str
    gemini_model: str = "gemini-3-flash-preview"
    video_fps: int = 2  # Higher FPS = more precise timestamps (default: 1)

    # Application Settings
    upload_dir: Path = Path("./uploads")
    output_dir: Path = Path("./outputs")

    # Shorts Configuration
    min_short_duration: int = 15  # seconds
    max_short_duration: int = 60  # seconds
    max_shorts_to_generate: int = 5

    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
