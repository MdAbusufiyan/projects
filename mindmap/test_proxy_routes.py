import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from mindmap import server as mindmap_server


@pytest.fixture
def client():
    mindmap_server.app.config['TESTING'] = True
    with mindmap_server.app.test_client() as client:
        yield client


def test_mapped_login_route_accepts_post(client):
    response = client.post('/exam/professor/login', data={'email': 'x', 'password': 'y'})
    assert response.status_code != 405


def test_proxy_preserves_redirects(monkeypatch):
    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(302)
            self.send_header('Location', '/professor/dashboard')
            self.end_headers()

        def log_message(self, format, *args):
            return

    httpd = HTTPServer(('127.0.0.1', 0), RedirectHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        monkeypatch.setattr(mindmap_server, 'EXAM_TARGET', f'http://127.0.0.1:{httpd.server_port}')
        response = mindmap_server.app.test_client().get('/exam/')
        assert response.status_code == 302
        assert response.headers['Location'] == '/exam/professor/dashboard'
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=2)
