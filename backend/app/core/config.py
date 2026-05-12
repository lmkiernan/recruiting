from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    GITHUB_TOKEN: str
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()
