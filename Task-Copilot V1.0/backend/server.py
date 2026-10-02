"""Loopback HTTP bridge. Built frontend is served from the same origin."""

from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from .features import FeatureStore


class AppServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address, store: FeatureStore, token: str, assets: Path):
        super().__init__(address, AppHandler)
        self.store = store
        self.token = token
        self.assets = assets


class AppHandler(BaseHTTPRequestHandler):
    server: AppServer

    def log_message(self, format, *args):
        pass

    def _json(self, code: int, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        origin = self.headers.get("Origin")
        host = self.headers.get("Host", "")
        if origin and origin.rstrip("/") != f"http://{host}":
            return False
        return self.headers.get("X-Task-Token") == self.server.token

    def _body(self):
        size = int(self.headers.get("Content-Length", "0"))
        if size < 1 or size > 524288:
            raise ValueError("请求体大小无效")
        value = json.loads(self.rfile.read(size))
        if not isinstance(value, dict):
            raise ValueError("请求内容必须是对象")
        return value

    def _handle_api(self):
        if not self._authorized():
            return self._json(403, {"error": "无权访问"})
        segments = urlparse(self.path).path.strip("/").split("/")
        try:
            store = self.server.store
            method = self.command
            diary_token = self.headers.get("X-Diary-Token", "")
            if segments == ["api", "diary", "status"] and method == "GET":
                return self._json(200, store.diary_status())
            if segments == ["api", "diary", "unlock"] and method == "POST":
                return self._json(200, store.diary_unlock(self._body().get("password", "")))
            if segments == ["api", "diary", "security"] and method == "POST":
                return self._json(200, store.diary_security(self._body(), diary_token))
            if segments == ["api", "diary", "lock"] and method == "POST":
                store.diary_lock(diary_token); return self._json(200, {"ok": True})
            if len(segments) in (3, 4) and segments[:2] == ["api", "life"]:
                kind = segments[2]
                if len(segments) == 3:
                    if method == "GET": return self._json(200, store.life_records(kind, diary_token))
                    if method == "POST": return self._json(201, store.life_records(kind, diary_token, self._body()))
                else:
                    if method == "PATCH": return self._json(200, store.life_records(kind, diary_token, self._body(), segments[3]))
                    if method == "DELETE": return self._json(200, store.life_records(kind, diary_token, item_id=segments[3], delete=True))
            if segments == ["api", "projects"]:
                if method == "GET": return self._json(200, store.list_projects())
                if method == "POST": return self._json(201, store.save_project(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "projects"]:
                if method == "PATCH": return self._json(200, store.save_project(self._body(), segments[2]))
                if method == "DELETE":
                    store.delete_project(segments[2]); return self._json(200, {"ok": True})
            if len(segments) == 4 and segments[:2] == ["api", "tasks"] and segments[3] == "subtasks":
                if method == "GET": return self._json(200, store.list_subtasks(segments[2]))
                if method == "POST": return self._json(201, store.create_subtask(segments[2], self._body()))
            if len(segments) == 5 and segments[:2] == ["api", "tasks"] and segments[3] == "subtasks":
                if method == "PATCH": return self._json(200, store.update_subtask(segments[2], segments[4], self._body()))
                if method == "DELETE":
                    store.delete_subtask(segments[2], segments[4]); return self._json(200, {"ok": True})
            if segments == ["api", "terms"]:
                if method == "GET": return self._json(200, store.list_terms())
                if method == "POST": return self._json(201, store.save_term(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "terms"]:
                if method == "PATCH": return self._json(200, store.save_term(self._body(), segments[2]))
            if len(segments) == 4 and segments[:2] == ["api", "terms"] and segments[3] == "activate" and method == "POST":
                store.activate_term(segments[2]); return self._json(200, {"ok": True})
            if segments == ["api", "courses"]:
                if method == "GET": return self._json(200, store.list_courses())
                if method == "POST": return self._json(201, store.save_course(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "courses"]:
                if method == "PATCH": return self._json(200, store.save_course(self._body(), segments[2]))
                if method == "DELETE":
                    store.delete_course(segments[2]); return self._json(200, {"ok": True})
            if segments == ["api", "occurrences"] and method == "GET":
                query = parse_qs(urlparse(self.path).query)
                return self._json(200, store.occurrences(query.get("start", [""])[0], query.get("end", [""])[0]))
            if segments == ["api", "exceptions"]:
                if method == "GET": return self._json(200, store.list_exceptions())
                if method == "POST": return self._json(201, store.save_exception(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "exceptions"] and method == "DELETE":
                store.delete_exception(segments[2]); return self._json(200, {"ok": True})
            if len(segments) == 4 and segments[:2] == ["api", "exceptions"] and segments[3] == "cancel" and method == "POST":
                return self._json(200, store.cancel_exception(segments[2]))
            if segments == ["api", "focus"] and method == "GET":
                return self._json(200, {"current": store.focus_current(), "history": store.focus_history()})
            if segments == ["api", "focus", "stats"] and method == "GET":
                return self._json(200, store.focus_statistics())
            if segments == ["api", "focus", "start"] and method == "POST":
                return self._json(201, store.focus_start(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "focus"] and method == "POST":
                return self._json(200, store.focus_action(segments[2]))
            if segments == ["api", "settings"]:
                if method == "GET": return self._json(200, store.settings())
                if method == "PATCH": return self._json(200, store.update_settings(self._body()))
            if segments == ["api", "tasks"]:
                if self.command == "GET":
                    return self._json(200, self.server.store.list_tasks())
                if self.command == "POST":
                    return self._json(201, self.server.store.create_task(self._body()))
            if len(segments) == 3 and segments[:2] == ["api", "tasks"]:
                task_id = segments[2]
                if self.command == "PATCH":
                    return self._json(200, self.server.store.update_task(task_id, self._body()))
                if self.command == "DELETE":
                    self.server.store.delete_task(task_id)
                    return self._json(200, {"ok": True})
            self._json(404, {"error": "接口不存在"})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
        except LookupError as exc:
            self._json(404, {"error": str(exc)})
        except Exception:
            self._json(500, {"error": "服务器内部错误"})

    def do_GET(self):
        if urlparse(self.path).path.startswith("/api/"):
            return self._handle_api()
        raw = unquote(urlparse(self.path).path)
        relative = "index.html" if raw in ("/", "") else raw.lstrip("/")
        root = self.server.assets.resolve()
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return self.send_error(404)
        content = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Cache-Control", "no-store" if path.name == "index.html" else "public, max-age=86400")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        self._handle_api()

    def do_PATCH(self):
        self._handle_api()

    def do_DELETE(self):
        self._handle_api()
