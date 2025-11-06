from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    city: str = "Bandung"
    days: int = 7
    timezone: str = "Asia/Jakarta"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
