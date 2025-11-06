from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    city: str = "Bandung"
    days: int = 7
    timezone: str = "Asia/Jakarta"
    # Make gemini_api_key optional to avoid hard crash when not set in dev.
    gemini_api_key: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

# Try to proactively load .env into the process environment. This makes
# behavior deterministic regardless of the current working directory or
# whether pydantic automatically reads env files in the running environment.
from dotenv import load_dotenv
load_dotenv()


settings = Settings()

print("\nSettings loaded:")
import os
print(f"- cwd: {os.getcwd()}")
print(f"- .env path exists: {os.path.exists('.env')}")
print(f"- GEMINI_API_KEY set: {'Yes' if settings.gemini_api_key else 'No'}")
print(f"- City: {settings.city}")
print(f"- Timezone: {settings.timezone}")
