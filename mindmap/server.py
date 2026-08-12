from flask import Flask, Response, request, send_from_directory
import os
import re
import threading
import webbrowser
from http import cookiejar
from urllib import request as urllib_request
from urllib.error import HTTPError, URLError

HOST = "127.0.0.1"
PORT = 8765
MASKED_ROUTE_ROOT = "/exam/"
EXAM_TARGET = os.getenv("EXAM_TARGET", "http://127.0.0.1:8520")

WEB_FOLDER = os.path.join(os.path.dirname(__file__), "web")
MINDMAP_FOLDER = os.path.join(WEB_FOLDER, "branch")

app = Flask(__name__, static_folder=WEB_FOLDER)
COOKIE_JAR = cookiejar.CookieJar()


class _NoRedirectHandler(urllib_request.HTTPRedirectHandler):
    def redirect_request(self, req, response, code, msg, headers):
        return None


def _rewrite_internal_links(body):
    if not isinstance(body, str):
        return body

    rewritten = re.sub(r'(["\'])/(?!/)(?!exam(?:/|$))', r'\1/exam/', body)
    rewritten = re.sub(r'url\(/(?!/)', 'url(/exam/', rewritten)
    return rewritten


def _prefix_for_exam(url):
    if not url:
        return url
    if url.startswith(("http://", "https://", "//", "mailto:", "tel:")):
        return url
    if url.startswith("/exam"):
        return url
    return f"/exam{url}" if url.startswith("/") else f"/exam/{url}"


def _proxy_to_exam(path, method, query_string, headers, data):
    upstream_path = "/" if not path else f"/{path}"
    target_url = f"{EXAM_TARGET}{upstream_path}"

    if query_string:
        target_url = f"{target_url}?{query_string.decode('utf-8')}"

    upstream_request = urllib_request.Request(target_url, method=method)

    for header_name, header_value in headers.items():
        if header_name.lower() in {"host", "content-length"}:
            continue
        upstream_request.add_header(header_name, header_value)

    if "cookie" in headers:
        upstream_request.add_header("Cookie", headers.get("Cookie"))

    if method in {"POST", "PUT", "PATCH"}:
        upstream_request.data = data

    try:
        opener = urllib_request.build_opener(
            _NoRedirectHandler,
            urllib_request.HTTPCookieProcessor(COOKIE_JAR),
        )
        with opener.open(upstream_request, timeout=15) as upstream_response:
            body = upstream_response.read()

            headers_out = {
                key: value
                for key, value in upstream_response.headers.items()
                if key.lower() not in {
                    "content-length",
                    "transfer-encoding",
                    "connection",
                    "date",
                    "server",
                }
            }

            content_type = upstream_response.headers.get("Content-Type", "")

            if "text/html" in content_type or "application/xhtml+xml" in content_type:
                text_body = body.decode("utf-8", errors="ignore")
                body = _rewrite_internal_links(text_body).encode("utf-8")

            location = headers_out.get("Location")
            if location:
                headers_out["Location"] = _prefix_for_exam(location)

            response = Response(body, status=upstream_response.status, headers=headers_out)
            response.autocorrect_location_header = False
            response.headers["Content-Type"] = content_type or "text/plain"
            return response

    except HTTPError as exc:
        body = exc.read()

        headers_out = {
            key: value
            for key, value in exc.headers.items()
            if key.lower() not in {
                "content-length",
                "transfer-encoding",
                "connection",
                "date",
                "server",
            }
        }

        response = Response(body, status=exc.code, headers=headers_out)
        response.headers["Content-Type"] = exc.headers.get("Content-Type", "text/plain")
        return response

    except URLError as exc:
        return Response(f"Unable to reach the Exam service: {exc}", status=502)


@app.route("/")
def index():
    return send_from_directory(WEB_FOLDER, "index.html")


@app.route("/mindmap/")
def mindmap_index():
    return send_from_directory(MINDMAP_FOLDER, "Mindmap.html")

@app.route("/green/")
def green_index():
    return send_from_directory(MINDMAP_FOLDER, "Green.html")


@app.route("/mindmap/<path:path>")
def mindmap_static(path):
    return send_from_directory(MINDMAP_FOLDER, path)


@app.route("/exam", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route(MASKED_ROUTE_ROOT, methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
@app.route(MASKED_ROUTE_ROOT + "<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def exam_proxy(path=""):
    return _proxy_to_exam(
        path,
        request.method,
        request.query_string,
        request.headers,
        request.get_data(),
    )


@app.route("/<path:path>", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
def static_files(path):
    local_path = os.path.join(WEB_FOLDER, path)

    if os.path.exists(local_path) and not os.path.isdir(local_path):
        return send_from_directory(WEB_FOLDER, path)

    return _proxy_to_exam(
        path,
        request.method,
        request.query_string,
        request.headers,
        request.get_data(),
    )


def open_browser():
    webbrowser.open(f"http://{HOST}:{PORT}")


if __name__ == "__main__":
    threading.Timer(1.0, open_browser).start()

    app.run(
        host=HOST,
        port=PORT,
        debug=False,
        use_reloader=False,
    )