from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from app.domain.contracts import RuntimeMode


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="PIPELINEPILOT_", extra="ignore")

    app_name: str = "PipelinePilot"
    mode: RuntimeMode = RuntimeMode.FIXTURE
    database_path: str = "./pipelinepilot.sqlite3"
    cors_origins: str = ""
    redaction_patterns: tuple[str, ...] = ("email", "card", "identifier")
    coco_enabled: bool = False
    coco_command: str = "cortex"
    coco_connection: str | None = None
    coco_timeout_seconds: float = 45.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip().rstrip("/")
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
