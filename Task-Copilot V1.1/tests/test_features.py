import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.features import FeatureStore
from agent import Agent


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = FeatureStore(Path(self.temp.name) / "taskcopilot.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_project_subtask_and_preserved_task(self):
        project = self.store.save_project({"name": "课程项目"})
        task = self.store.create_task({"title": "完成报告", "project_id": project["id"]})
        sub = self.store.create_subtask(task["id"], {"title": "搜集资料"})
        self.store.update_subtask(task["id"], sub["id"], {"done": True})
        listed = self.store.list_tasks()[0]
        self.assertEqual((listed["subtask_total"], listed["subtask_done"]), (1, 1))
        self.store.delete_project(project["id"])
        self.assertIsNone(self.store.list_tasks()[0]["project_id"])

    def test_odd_week_and_one_day_move(self):
        term = self.store.save_term({"name": "秋季", "start_date": "2026-09-28", "weeks": 18})
        course = self.store.save_course({"term_id": term["id"], "name": "高数", "weekday": 1,
                                         "start_time": "09:00", "end_time": "10:30", "start_week": 1,
                                         "end_week": 18, "week_type": "odd"})
        rows = self.store.list_courses()
        self.assertEqual([o["date"] for o in self.store.occurrences("2026-09-28", "2026-10-20")],
                         ["2026-09-28", "2026-10-12"])
        self.store.save_exception({"course_id": course["id"], "rule_id": rows[0]["rules"][0]["rule_id"],
                                   "original_date": "2026-10-12", "action": "move",
                                   "target_date": "2026-10-13", "start_time": "11:00", "end_time": "12:30"})
        occurrences = self.store.occurrences("2026-10-12", "2026-10-20")
        self.assertEqual([(o["date"], o["start_time"]) for o in occurrences], [("2026-10-13", "11:00")])

    def test_one_course_can_have_multiple_weekly_rules(self):
        term = self.store.save_term({"name": "秋季", "start_date": "2026-09-28", "weeks": 18})
        course = self.store.save_course({
            "term_id": term["id"], "name": "大学英语",
            "rules": [
                {"weekday": 2, "start_time": "08:00", "end_time": "09:30", "start_week": 1, "end_week": 18, "week_type": "all"},
                {"weekday": 4, "start_time": "14:00", "end_time": "15:30", "start_week": 1, "end_week": 18, "week_type": "all"},
            ],
        })
        listed = self.store.list_courses()
        self.assertEqual(len(listed), 1)
        self.assertEqual(len(listed[0]["rules"]), 2)
        occurrences = self.store.occurrences("2026-09-28", "2026-10-05")
        self.assertEqual([(o["date"], o["start_time"]) for o in occurrences],
                         [("2026-09-29", "08:00"), ("2026-10-01", "14:00")])
        first_rule = listed[0]["rules"][0]
        self.store.save_course({
            "name": "大学英语", "rules": [
                {**first_rule, "weekday": 3},
                {"weekday": 5, "start_time": "16:00", "end_time": "17:30", "start_week": 1, "end_week": 18, "week_type": "odd"},
            ],
        }, course["id"])
        self.assertEqual(len(self.store.list_courses()[0]["rules"]), 2)

    def test_focus_and_reminder_deduplication(self):
        started = self.store.focus_start({})
        self.assertEqual(started["status"], "running")
        self.store.focus_action("pause")
        self.store.focus_action("resume")
        self.assertEqual(self.store.focus_action("stop")["status"], "finished")
        scheduled = datetime.now(timezone.utc).isoformat()
        self.assertTrue(self.store.claim_reminder("task", "a", "a", 60, scheduled))
        self.assertFalse(self.store.claim_reminder("task", "a", "a", 60, scheduled))

    def test_agent_reminder_respects_pause_and_deduplicates(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        self.store.create_task({"title": "测试提醒", "due_at": (now + timedelta(minutes=60)).isoformat()})
        agent = Agent(Path(self.temp.name))
        sent = []
        self.assertEqual(agent.scan_reminders(now, lambda title, message: sent.append((title, message))), 1)
        self.assertEqual(agent.scan_reminders(now, lambda title, message: sent.append((title, message))), 0)
        self.assertEqual(len(sent), 1)
        self.store.update_settings({"reminders_paused": True})
        self.assertEqual(agent.scan_reminders(now, lambda title, message: sent.append((title, message))), 0)


if __name__ == "__main__":
    unittest.main()
