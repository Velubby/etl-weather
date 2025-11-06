import os, traceback
from dotenv import load_dotenv
print('Before load_dotenv, GEMINI in os.environ:', 'GEMINI_API_KEY' in os.environ)
load_dotenv('.env')
print('After load_dotenv, GEMINI in os.environ:', 'GEMINI_API_KEY' in os.environ)
print('GEMINI value (start):', (os.environ.get('GEMINI_API_KEY')[:10] + '...') if os.environ.get('GEMINI_API_KEY') else None)
try:
    # Import config module which uses pydantic-settings
    from etl_weather import config
    # instantiate a fresh Settings to avoid import-time prints (config already creates one at import)
    from pydantic_settings import BaseSettings, SettingsConfigDict
    class _S(BaseSettings):
        gemini_api_key: str | None = None
        model_config = SettingsConfigDict(env_file='.env')
    s = _S()
    print('fresh _S.gemini_api_key:', repr(s.gemini_api_key))
    print('config.settings.gemini_api_key (existing):', repr(config.settings.gemini_api_key))
except Exception as e:
    traceback.print_exc()
    print('ERR', e)
