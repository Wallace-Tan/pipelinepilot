from functools import lru_cache

from pydantic import ConfigDict
from pydantic_settings import BaseSettings

from app.domain.contracts import RuntimeMode


class Settings(BaseSettings):
    model_config = ConfigDict(env_prefix="PIPELINEPILOT_", extra="ignore")

    app_name: str = "PipelinePilot"
    mode: RuntimeMode = RuntimeMode.FIXTURE


@lru_cache
def get_settings() -> Settings:
    return Settings()
