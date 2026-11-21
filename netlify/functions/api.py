"""
Netlify Serverless Function Handler for BTMS-3D Pro API
Bridges incoming AWS Lambda / Netlify serverless HTTP events to the Flask WSGI application.
Supports all 180-cell thermal solver, MHD momentum, localized hotspot, and inspection endpoints.
"""

import sys
import os
import io
import json
import base64
from urllib.parse import urlencode

# Ensure project root is available in sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure Matplotlib non-interactive backend for headless serverless execution
os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

try:
    from btms_3d.backend.app import app
except ImportError as err:
    app = None
    import_error_msg = str(err)


def handler(event, context):
    """
    Netlify Function Entrypoint.
    Transforms AWS Lambda / Netlify event into standard WSGI environment.
    """
    http_method = event.get("httpMethod", "GET").upper()

    # Handle CORS Preflight OPTIONS requests
    if http_method == "OPTIONS":
        return {
            "statusCode": 204,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
                "Access-Control-Max-Age": "86400"
            },
            "body": ""
        }

    if app is None:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"success": False, "error": f"Failed to initialize Flask app: {import_error_msg}"})
        }

    # Extract & normalize requested path
    raw_path = event.get("path", "/")
    if "/.netlify/functions/api" in raw_path:
        path = raw_path.split("/.netlify/functions/api", 1)[1]
    else:
        path = raw_path

    if not path.startswith("/"):
        path = "/" + path

    # Extract query parameters
    query_params = event.get("queryStringParameters") or {}
    query_string = urlencode(query_params)

    # Process request body
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded", False):
        try:
            body_bytes = base64.b64decode(body)
        except Exception:
            body_bytes = b""
    else:
        body_bytes = body.encode("utf-8") if isinstance(body, str) else body

    input_stream = io.BytesIO(body_bytes)
    headers = event.get("headers") or {}

    # Construct standard WSGI environment dictionary
    environ = {
        "REQUEST_METHOD": http_method,
        "SCRIPT_NAME": "",
        "PATH_INFO": path,
        "QUERY_STRING": query_string,
        "SERVER_NAME": "netlify",
        "SERVER_PORT": "443",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "https",
        "wsgi.input": input_stream,
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "CONTENT_TYPE": headers.get("content-type", headers.get("Content-Type", "application/json")),
    }

    # Map headers to HTTP_* environment variables
    for k, v in headers.items():
        key = "HTTP_" + k.upper().replace("-", "_")
        environ[key] = str(v)

    status_code = [200]
    response_headers = []

    def start_response(status, resp_hdrs, exc_info=None):
        code = int(status.split(" ")[0])
        status_code[0] = code
        response_headers.extend(resp_hdrs)

    try:
        response_iter = app.wsgi_app(environ, start_response)
        response_body = b"".join(response_iter)
    except Exception as exc:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({"success": False, "error": f"Serverless execution exception: {str(exc)}"})
        }

    resp_headers_dict = {k: v for k, v in response_headers}
    resp_headers_dict["Access-Control-Allow-Origin"] = "*"

    return {
        "statusCode": status_code[0],
        "headers": resp_headers_dict,
        "body": response_body.decode("utf-8", errors="replace"),
        "isBase64Encoded": False
    }
