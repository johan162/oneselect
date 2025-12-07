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

    # Google OAuth Settings
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    FRONTEND_URL: str = "http://localhost:3000"

    # Bayesian Comparison Settings
    # Multiplier for "much better" graded comparisons (a_much_better, b_much_better).
    # A value of 2.0 means "much better" provides twice the information of "better".
    # This accelerates score convergence for strong preferences.
    GRADED_MUCH_BETTER_MULTIPLIER: float = 2.0

    # Multiplier for "equal" graded comparisons.
    # A value of 1.0 treats "equal" as equally informative as "better".
    # A lower value (e.g., 0.5) would treat ties as less informative,
    # useful if users tend to select "equal" when uncertain rather than confident.
    GRADED_EQUAL_MULTIPLIER: float = 0.8

    model_config = SettingsConfigDict(case_sensitive=True)


settings = Settings()
