from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "OneSelect API"
    API_V1_STR: str = "/v1"
    SECRET_KEY: str = "YOUR_SECRET_KEY_HERE_CHANGE_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Database
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///./oneselect.db"

    FIRST_SUPERUSER: str = "admin@example.com"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    BACKEND_CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
