import tempfile
import unittest
from pathlib import Path

from backend.store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "tasks.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_task_lifecycle_persists_across_instances(self):
        created = self.store.create_task({
            "title": "  完成作业  ", "kind": "homework", "priority": "high",
            "due_at": "2026-10-03T22:00:00+08:00",
        })
        self.assertEqual(created["title"], "完成作业")
        self.assertEqual(created["due_at"], "2026-10-03T14:00:00+00:00")
        self.assertEqual(len(Store(self.store.path).list_tasks()), 1)
        completed = self.store.update_task(created["id"], {"status": "done"})
        self.assertIsNotNone(completed["completed_at"])
        reopened = self.store.update_task(created["id"], {"status": "todo", "title": "复查作业"})
        self.assertIsNone(reopened["completed_at"])
        self.assertEqual(reopened["title"], "复查作业")
        self.store.delete_task(created["id"])
        self.assertEqual(self.store.list_tasks(), [])

    def test_rejects_invalid_payload(self):
        with self.assertRaises(ValueError):
            self.store.create_task({"title": " "})
        with self.assertRaises(ValueError):
            self.store.create_task({"title": "事项", "due_at": "2026-10-03T22:00:00"})
        created = self.store.create_task({"title": "事项"})
        with self.assertRaises(ValueError):
            self.store.update_task(created["id"], {"status": "unknown"})


if __name__ == "__main__":
    unittest.main()
