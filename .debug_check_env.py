import os, traceback
print('CWD:', os.getcwd())
print('.env exists:', os.path.exists('.env'))
print('GEMINI in os.environ:', 'GEMINI_API_KEY' in os.environ)
print('GEMINI value (start):', (os.environ.get('GEMINI_API_KEY')[:10] + '...') if os.environ.get('GEMINI_API_KEY') else None)
try:
    from etl_weather.config import settings
    print('settings.gemini_api_key:', repr(settings.gemini_api_key))
except Exception as e:
    traceback.print_exc()
    print('IMPORT-ERROR:', e)
