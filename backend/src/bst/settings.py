from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False
    database_path: str = "data/bst.db"
    openai_api_key: str = Field(default="", repr=False)
    openai_model: str = "gpt-5.4-nano"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"


settings = Settings()
