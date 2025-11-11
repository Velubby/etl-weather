import os
import sys

# Ensure project root is on sys.path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Ensure src/ is on sys.path for src-layout projects
SRC_DIR = os.path.join(APP_DIR, "src")
if os.path.isdir(SRC_DIR) and SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import FastAPI ASGI app
from etl_weather.web import app as asgi_app

# Wrap ASGI app into WSGI for Passenger
# Try multiple import paths for compatibility
application = None

try:
    # Try asgiref 3.x location
    from asgiref.wsgi import AsgiToWsgi

    application = AsgiToWsgi(asgi_app)
except (ImportError, AttributeError):
    try:
        # Try a2wsgi as alternative
        from a2wsgi import ASGIMiddleware

        application = ASGIMiddleware(asgi_app)
    except ImportError:
        # Manual WSGI wrapper as last resort
        import asyncio
        import io

        def application(environ, start_response):
            """Manual ASGI->WSGI adapter"""
            # Create new event loop for this request
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Build ASGI scope from WSGI environ
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0"},
                    "http_version": "1.1",
                    "method": environ["REQUEST_METHOD"],
                    "path": environ.get("PATH_INFO", "/"),
                    "query_string": environ.get("QUERY_STRING", "").encode(),
                    "headers": [
                        (k.lower().replace("_", "-").encode(), v.encode())
                        for k, v in environ.items()
                        if k.startswith("HTTP_")
                    ],
                    "server": (
                        environ.get("SERVER_NAME", "localhost"),
                        int(environ.get("SERVER_PORT", 80)),
                    ),
                }

                # Response storage
                response_started = False
                status_code = 200
                headers = []
                body_parts = []

                async def receive():
                    # Read request body if present
                    body = environ.get("wsgi.input", io.BytesIO()).read()
                    return {"type": "http.request", "body": body}

                async def send(message):
                    nonlocal response_started, status_code, headers
                    if message["type"] == "http.response.start":
                        status_code = message["status"]
                        headers = message.get("headers", [])
                        response_started = True
                    elif message["type"] == "http.response.body":
                        body_parts.append(message.get("body", b""))

                # Run ASGI app
                loop.run_until_complete(asgi_app(scope, receive, send))

                # Send WSGI response
                status_text = f"{status_code} OK"
                response_headers = [(k.decode(), v.decode()) for k, v in headers]
                start_response(status_text, response_headers)

                return [b"".join(body_parts)]

            finally:
                loop.close()
