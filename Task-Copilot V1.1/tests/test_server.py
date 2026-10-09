import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from backend.server import AppServer
from backend.features import FeatureStore


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "index.html").write_text("<h1>Task Copilot</h1>", encoding="utf-8")
        self.server = AppServer(("127.0.0.1", 0), FeatureStore(root / "tasks.db"), "test-token", root)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def request(self, path, method="GET", payload=None, token="test-token"):
        headers = {"X-Task-Token": token}
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(f"http://127.0.0.1:{self.server.server_port}{path}", body, headers, method=method)
        with urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_create_complete_and_read_back(self):
        task = self.request("/api/tasks", "POST", {"title": "准备考试", "kind": "exam", "priority": "high"})
        self.assertEqual(len(self.request("/api/tasks")), 1)
        updated = self.request(f"/api/tasks/{task['id']}", "PATCH", {"status": "done"})
        self.assertEqual(updated["status"], "done")
        self.assertIsNotNone(updated["completed_at"])

    def test_rejects_missing_token(self):
        with self.assertRaises(HTTPError) as result:
            self.request("/api/tasks", token="")
        self.assertEqual(result.exception.code, 403)

    def test_schedule_project_focus_and_settings_endpoints(self):
        term = self.request("/api/terms", "POST", {"name": "秋季", "start_date": "2026-09-28", "weeks": 18})
        self.request("/api/courses", "POST", {"term_id": term["id"], "name": "英语", "weekday": 4,
            "start_time": "09:00", "end_time": "10:30", "start_week": 1, "end_week": 18,
            "week_type": "all"})
        rows = self.request("/api/occurrences?start=2026-10-01&end=2026-10-02")
        self.assertEqual(rows[0]["name"], "英语")
        project = self.request("/api/projects", "POST", {"name": "期末项目"})
        task = self.request("/api/tasks", "POST", {"title": "查资料", "project_id": project["id"]})
        self.request(f"/api/tasks/{task['id']}/subtasks", "POST", {"title": "图书馆"})
        self.assertEqual(len(self.request(f"/api/tasks/{task['id']}/subtasks")), 1)
        self.request("/api/focus/start", "POST", {"task_id": task["id"]})
        self.assertEqual(self.request("/api/focus")["current"]["status"], "running")
        self.request("/api/focus/stop", "POST", {})
        self.assertEqual(self.request("/api/focus/stats")["total_seconds"], 0)
        settings = self.request("/api/settings", "PATCH", {"reminders_paused": True})
        self.assertEqual(settings["reminders_paused"], "true")


if __name__ == "__main__":
    unittest.main()
