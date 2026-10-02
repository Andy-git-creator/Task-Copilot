"""Project, schedule, focus and reminder operations shared by UI and agent."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timedelta, timezone

from .store import Store, utc_now
from .life import LifeMixin


def uid():
    return uuid.uuid4().hex


def required_text(value, label, maximum=120):
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        raise ValueError(f"{label}需为 1–{maximum} 个字符")
    return text


def optional_text(value, maximum=500):
    text = str(value or "").strip()
    if len(text) > maximum:
        raise ValueError(f"内容不能超过 {maximum} 个字符")
    return text


def iso_date(value):
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("日期格式应为 YYYY-MM-DD") from exc
    return parsed


def clock_time(value):
    try:
        parsed = datetime.strptime(value, "%H:%M").time()
    except (TypeError, ValueError) as exc:
        raise ValueError("时间格式应为 HH:MM") from exc
    return parsed.strftime("%H:%M")


class FeatureStore(LifeMixin, Store):
    def list_projects(self):
        with self.connect() as db:
            rows = db.execute("""
                SELECT p.*, COUNT(t.id) AS task_total,
                    COALESCE(SUM(CASE WHEN t.status='done' THEN 1 ELSE 0 END),0) AS task_done
                FROM projects p LEFT JOIN tasks t ON t.project_id=p.id
                GROUP BY p.id ORDER BY p.created_at DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def save_project(self, payload, project_id=None):
        name = required_text(payload.get("name"), "项目名称")
        description = optional_text(payload.get("description"), 1000)
        status = payload.get("status", "active")
        if status not in ("active", "completed"):
            raise ValueError("项目状态无效")
        due_at = self._validate_due(payload.get("due_at"))
        now = utc_now()
        with self.connect() as db:
            if project_id:
                if not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                    raise LookupError("项目不存在")
                db.execute("UPDATE projects SET name=?,description=?,status=?,due_at=?,updated_at=? WHERE id=?",
                           (name, description, status, due_at, now, project_id))
            else:
                project_id = uid()
                db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?,?)",
                           (project_id, name, description, status, due_at, now, now))
            return dict(db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone())

    def delete_project(self, project_id):
        with self.connect() as db:
            if not db.execute("DELETE FROM projects WHERE id=?", (project_id,)).rowcount:
                raise LookupError("项目不存在")

    def list_subtasks(self, task_id):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise LookupError("任务不存在")
            return [dict(r) for r in db.execute("SELECT * FROM subtasks WHERE task_id=? ORDER BY position,created_at", (task_id,))]

    def create_subtask(self, task_id, payload):
        title = required_text(payload.get("title"), "子任务标题")
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise LookupError("任务不存在")
            position = db.execute("SELECT COALESCE(MAX(position),-1)+1 FROM subtasks WHERE task_id=?", (task_id,)).fetchone()[0]
            item_id, now = uid(), utc_now()
            db.execute("INSERT INTO subtasks VALUES (?,?,?,?,?,?,?)", (item_id, task_id, title, 0, position, now, now))
            return dict(db.execute("SELECT * FROM subtasks WHERE id=?", (item_id,)).fetchone())

    def update_subtask(self, task_id, subtask_id, payload):
        if not isinstance(payload, dict) or not payload or set(payload) - {"title", "done"}:
            raise ValueError("子任务字段无效")
        with self.connect() as db:
            row = db.execute("SELECT * FROM subtasks WHERE id=? AND task_id=?", (subtask_id, task_id)).fetchone()
            if not row:
                raise LookupError("子任务不存在")
            title = required_text(payload.get("title", row["title"]), "子任务标题")
            done = int(bool(payload.get("done", row["done"])))
            db.execute("UPDATE subtasks SET title=?,done=?,updated_at=? WHERE id=?", (title, done, utc_now(), subtask_id))
            return dict(db.execute("SELECT * FROM subtasks WHERE id=?", (subtask_id,)).fetchone())

    def delete_subtask(self, task_id, subtask_id):
        with self.connect() as db:
            if not db.execute("DELETE FROM subtasks WHERE id=? AND task_id=?", (subtask_id, task_id)).rowcount:
                raise LookupError("子任务不存在")

    def list_terms(self):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM terms ORDER BY start_date DESC")]

    def save_term(self, payload, term_id=None):
        name = required_text(payload.get("name"), "学期名称")
        start = iso_date(payload.get("start_date"))
        if start.weekday() != 0:
            raise ValueError("学期第一周日期必须是星期一")
        weeks = int(payload.get("weeks", 18))
        if not 1 <= weeks <= 32:
            raise ValueError("学期周数需在 1–32 之间")
        with self.connect() as db:
            if term_id:
                if not db.execute("SELECT 1 FROM terms WHERE id=?", (term_id,)).fetchone():
                    raise LookupError("学期不存在")
                db.execute("UPDATE terms SET name=?,start_date=?,weeks=? WHERE id=?", (name, start.isoformat(), weeks, term_id))
            else:
                term_id = uid()
                db.execute("UPDATE terms SET is_active=0")
                db.execute("INSERT INTO terms VALUES (?,?,?,?,1)", (term_id, name, start.isoformat(), weeks))
            return dict(db.execute("SELECT * FROM terms WHERE id=?", (term_id,)).fetchone())

    def activate_term(self, term_id):
        with self.connect() as db:
            if not db.execute("SELECT 1 FROM terms WHERE id=?", (term_id,)).fetchone():
                raise LookupError("学期不存在")
            db.execute("UPDATE terms SET is_active=0")
            db.execute("UPDATE terms SET is_active=1 WHERE id=?", (term_id,))

    def list_courses(self, term_id=None):
        with self.connect() as db:
            if term_id is None:
                row = db.execute("SELECT id FROM terms WHERE is_active=1 LIMIT 1").fetchone()
                term_id = row["id"] if row else ""
            rows = db.execute("""
                SELECT c.*,r.id AS rule_id,r.weekday,r.start_time,r.end_time,r.start_week,r.end_week,r.week_type
                FROM courses c JOIN course_rules r ON r.course_id=c.id
                WHERE c.term_id=? ORDER BY r.weekday,r.start_time
            """, (term_id,)).fetchall()
            courses = {}
            for row in rows:
                item = dict(row)
                course_id = item["id"]
                if course_id not in courses:
                    courses[course_id] = {key: item[key] for key in (
                        "id", "term_id", "name", "teacher", "location", "color", "created_at", "updated_at"
                    )}
                    courses[course_id]["rules"] = []
                courses[course_id]["rules"].append({key: item[key] for key in (
                    "rule_id", "weekday", "start_time", "end_time", "start_week", "end_week", "week_type"
                )})
            return list(courses.values())

    def save_course(self, payload, course_id=None):
        name = required_text(payload.get("name"), "课程名称")
        teacher = optional_text(payload.get("teacher"), 120)
        location = optional_text(payload.get("location"), 120)
        color = payload.get("color", "#5c9394")
        if not isinstance(color, str) or len(color) != 7 or color[0] != "#" or any(c not in "0123456789abcdefABCDEF" for c in color[1:]):
            raise ValueError("课程颜色无效")
        raw_rules = payload.get("rules")
        if raw_rules is None:
            raw_rules = [{key: payload.get(key) for key in (
                "rule_id", "weekday", "start_time", "end_time", "start_week", "end_week", "week_type"
            )}]
        if not isinstance(raw_rules, list) or not 1 <= len(raw_rules) <= 14:
            raise ValueError("一门课程需设置 1–14 个上课时段")
        rules = []
        for raw in raw_rules:
            if not isinstance(raw, dict):
                raise ValueError("课程时段格式无效")
            weekday = int(raw.get("weekday", 1))
            start_time = clock_time(raw.get("start_time"))
            end_time = clock_time(raw.get("end_time"))
            start_week = int(raw.get("start_week", 1))
            end_week = int(raw.get("end_week", 18))
            week_type = raw.get("week_type", "all")
            if not 1 <= weekday <= 7 or start_time >= end_time or week_type not in ("all", "odd", "even"):
                raise ValueError("上课日期、时间或单双周无效")
            rules.append({"rule_id": raw.get("rule_id"), "weekday": weekday, "start_time": start_time,
                          "end_time": end_time, "start_week": start_week, "end_week": end_week,
                          "week_type": week_type})
        with self.connect() as db:
            term_id = payload.get("term_id")
            if course_id:
                original = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
                if not original:
                    raise LookupError("课程不存在")
                term_id = term_id or original["term_id"]
            if not term_id:
                row = db.execute("SELECT id FROM terms WHERE is_active=1 LIMIT 1").fetchone()
                term_id = row["id"] if row else None
            term = db.execute("SELECT * FROM terms WHERE id=?", (term_id,)).fetchone() if term_id else None
            if not term:
                raise ValueError("请先建立学期")
            if any(not 1 <= rule["start_week"] <= rule["end_week"] <= term["weeks"] for rule in rules):
                raise ValueError("课程周次超出学期范围")
            signatures = [(r["weekday"], r["start_time"], r["end_time"], r["start_week"], r["end_week"], r["week_type"]) for r in rules]
            if len(signatures) != len(set(signatures)):
                raise ValueError("不能添加完全相同的上课时段")
            now = utc_now()
            if course_id:
                db.execute("UPDATE courses SET name=?,teacher=?,location=?,color=?,updated_at=? WHERE id=?",
                           (name, teacher, location, color, now, course_id))
                existing = {r["id"] for r in db.execute("SELECT id FROM course_rules WHERE course_id=?", (course_id,))}
                retained = set()
                for rule in rules:
                    rule_id = rule["rule_id"]
                    if rule_id in existing:
                        db.execute("UPDATE course_rules SET weekday=?,start_time=?,end_time=?,start_week=?,end_week=?,week_type=? WHERE id=?",
                                   (rule["weekday"], rule["start_time"], rule["end_time"], rule["start_week"], rule["end_week"], rule["week_type"], rule_id))
                        retained.add(rule_id)
                    else:
                        rule_id = uid()
                        db.execute("INSERT INTO course_rules VALUES (?,?,?,?,?,?,?,?)",
                                   (rule_id, course_id, rule["weekday"], rule["start_time"], rule["end_time"], rule["start_week"], rule["end_week"], rule["week_type"]))
                        retained.add(rule_id)
                for rule_id in existing - retained:
                    db.execute("DELETE FROM course_rules WHERE id=?", (rule_id,))
            else:
                course_id = uid()
                db.execute("INSERT INTO courses VALUES (?,?,?,?,?,?,?,?)",
                           (course_id, term_id, name, teacher, location, color, now, now))
                for rule in rules:
                    db.execute("INSERT INTO course_rules VALUES (?,?,?,?,?,?,?,?)",
                               (uid(), course_id, rule["weekday"], rule["start_time"], rule["end_time"], rule["start_week"], rule["end_week"], rule["week_type"]))
            return dict(db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone())

    def delete_course(self, course_id):
        with self.connect() as db:
            if not db.execute("DELETE FROM courses WHERE id=?", (course_id,)).rowcount:
                raise LookupError("课程不存在")

    def save_exception(self, payload):
        action = payload.get("action")
        if action not in ("cancel", "move", "add"):
            raise ValueError("调课类型无效")
        course_id = payload.get("course_id")
        with self.connect() as db:
            course = db.execute("SELECT * FROM courses WHERE id=?", (course_id,)).fetchone()
            if not course:
                raise LookupError("课程不存在")
            rule_id = payload.get("rule_id")
            original_date = payload.get("original_date")
            if action != "add":
                if not rule_id or not db.execute("SELECT 1 FROM course_rules WHERE id=? AND course_id=?", (rule_id, course_id)).fetchone():
                    raise ValueError("课程规则不存在")
                original_date = iso_date(original_date).isoformat()
            else:
                rule_id, original_date = None, None
            target_date = iso_date(payload.get("target_date")).isoformat() if action != "cancel" else None
            start_time = clock_time(payload.get("start_time")) if action != "cancel" else None
            end_time = clock_time(payload.get("end_time")) if action != "cancel" else None
            if start_time and start_time >= end_time:
                raise ValueError("结束时间需晚于开始时间")
            location = optional_text(payload.get("location"), 120)
            teacher = optional_text(payload.get("teacher"), 120)
            if rule_id:
                db.execute("UPDATE course_exceptions SET active=0 WHERE rule_id=? AND original_date=? AND active=1", (rule_id, original_date))
            item_id = uid()
            db.execute("INSERT INTO course_exceptions (id,course_id,rule_id,original_date,action,target_date,start_time,end_time,location,teacher,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (item_id, course_id, rule_id, original_date, action, target_date, start_time, end_time, location, teacher, utc_now()))
            return dict(db.execute("SELECT * FROM course_exceptions WHERE id=?", (item_id,)).fetchone())

    def cancel_exception(self, exception_id):
        with self.connect() as db:
            if not db.execute("UPDATE course_exceptions SET active=0 WHERE id=?", (exception_id,)).rowcount:
                raise LookupError("调课记录不存在")
            return dict(db.execute("SELECT * FROM course_exceptions WHERE id=?", (exception_id,)).fetchone())

    def delete_exception(self, exception_id):
        with self.connect() as db:
            if not db.execute("UPDATE course_exceptions SET record_visible=0 WHERE id=? AND record_visible=1", (exception_id,)).rowcount:
                raise LookupError("调课记录不存在")

    def list_exceptions(self, term_id=None):
        with self.connect() as db:
            if not term_id:
                row = db.execute("SELECT id FROM terms WHERE is_active=1 LIMIT 1").fetchone()
                term_id = row["id"] if row else ""
            return [dict(r) for r in db.execute("""
                SELECT e.*,c.name AS course_name FROM course_exceptions e
                JOIN courses c ON c.id=e.course_id WHERE c.term_id=? AND e.record_visible=1 ORDER BY e.created_at DESC
            """, (term_id,))]

    def occurrences(self, start_date, end_date):
        start, end = iso_date(start_date), iso_date(end_date)
        if end <= start or (end - start).days > 60:
            raise ValueError("课表查询范围需在 1–60 天之间")
        with self.connect() as db:
            terms = [dict(r) for r in db.execute("SELECT * FROM terms WHERE is_active=1")]
            if not terms:
                return []
            term = terms[0]
            rules = [dict(r) for r in db.execute("""
                SELECT c.id AS course_id,c.name,c.teacher,c.location,c.color,r.*
                FROM courses c JOIN course_rules r ON r.course_id=c.id WHERE c.term_id=?
            """, (term["id"],))]
            exceptions = [dict(r) for r in db.execute("""
                SELECT e.* FROM course_exceptions e JOIN courses c ON c.id=e.course_id WHERE c.term_id=? AND e.active=1
            """, (term["id"],))]
        original_ex = {(e["rule_id"], e["original_date"]): e for e in exceptions if e["rule_id"]}
        course_map = {r["course_id"]: r for r in rules}
        result = []
        term_start = date.fromisoformat(term["start_date"])
        day = start
        while day < end:
            week = (day - term_start).days // 7 + 1
            if 1 <= week <= term["weeks"]:
                for rule in rules:
                    if rule["weekday"] != day.isoweekday() or not rule["start_week"] <= week <= rule["end_week"]:
                        continue
                    if rule["week_type"] == "odd" and week % 2 == 0 or rule["week_type"] == "even" and week % 2:
                        continue
                    ex = original_ex.get((rule["id"], day.isoformat()))
                    if ex:
                        continue
                    result.append(self._occurrence(rule, day.isoformat(), rule["start_time"], rule["end_time"], rule["location"], rule["teacher"], f"{rule['id']}:{day.isoformat()}", week))
            day += timedelta(days=1)
        for ex in exceptions:
            if ex["action"] == "cancel":
                continue
            target = date.fromisoformat(ex["target_date"])
            if not start <= target < end:
                continue
            course = course_map.get(ex["course_id"])
            if not course:
                continue
            course = dict(course)
            course["id"] = ex["rule_id"]
            week = (target - term_start).days // 7 + 1
            key = f"{ex['rule_id']}:{ex['original_date']}" if ex["rule_id"] else f"extra:{ex['id']}"
            result.append(self._occurrence(course, ex["target_date"], ex["start_time"], ex["end_time"], ex["location"] or course["location"], ex["teacher"] or course["teacher"], key, week, ex["id"], ex["original_date"]))
        return sorted(result, key=lambda row: (row["date"], row["start_time"], row["name"]))

    @staticmethod
    def _occurrence(course, day, start, end, location, teacher, key, week, exception_id=None, original_date=None):
        return {"course_id": course["course_id"], "rule_id": course["id"], "name": course["name"],
                "date": day, "start_time": start, "end_time": end, "location": location,
                "teacher": teacher, "color": course["color"], "occurrence_key": key,
                "week": week, "exception_id": exception_id, "original_date": original_date or day}

    def focus_current(self):
        with self.connect() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1").fetchone()
            return dict(row) if row else None

    def focus_history(self, limit=100):
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM focus_sessions ORDER BY started_at DESC LIMIT ?", (limit,))]

    def focus_start(self, payload):
        if self.focus_current():
            raise ValueError("已有未结束的专注记录")
        task_id, project_id = payload.get("task_id") or None, payload.get("project_id") or None
        with self.connect() as db:
            if task_id and not db.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise ValueError("任务不存在")
            if project_id and not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("项目不存在")
            item_id, now = uid(), utc_now()
            db.execute("INSERT INTO focus_sessions VALUES (?,?,?,?,?,?,?,?)", (item_id, task_id, project_id, now, None, now, 0, "running"))
            return dict(db.execute("SELECT * FROM focus_sessions WHERE id=?", (item_id,)).fetchone())

    def focus_tick(self):
        now = datetime.now(timezone.utc)
        with self.connect() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE status='running' ORDER BY started_at DESC LIMIT 1").fetchone()
            if not row:
                return
            previous = datetime.fromisoformat(row["last_tick_at"])
            delta = max(0, min(10, int((now - previous).total_seconds())))
            if delta:
                effective_end = previous + timedelta(seconds=delta)
                db.execute("INSERT INTO focus_segments VALUES (?,?,?,?,?)",
                           (uid(), row["id"], previous.isoformat(timespec="seconds"),
                            effective_end.isoformat(timespec="seconds"), delta))
            db.execute("UPDATE focus_sessions SET active_seconds=active_seconds+?,last_tick_at=? WHERE id=?",
                       (delta, now.isoformat(timespec="seconds"), row["id"]))

    def focus_statistics(self):
        local_now = datetime.now().astimezone()
        today = local_now.date()
        week_start = today - timedelta(days=today.weekday())
        daily = {(today - timedelta(days=i)).isoformat(): 0 for i in range(6, -1, -1)}
        today_seconds = week_seconds = total_seconds = 0
        with self.connect() as db:
            rows = db.execute("SELECT started_at,ended_at,effective_seconds FROM focus_segments").fetchall()
            legacy = db.execute("""SELECT started_at,active_seconds FROM focus_sessions s
                WHERE NOT EXISTS (SELECT 1 FROM focus_segments g WHERE g.session_id=s.id)""").fetchall()
        for row in rows:
            cursor = datetime.fromisoformat(row["started_at"]).astimezone()
            end = datetime.fromisoformat(row["ended_at"]).astimezone()
            total_seconds += row["effective_seconds"]
            while cursor < end:
                next_midnight = datetime.combine(cursor.date() + timedelta(days=1), datetime.min.time(), tzinfo=cursor.tzinfo)
                piece_end = min(end, next_midnight)
                seconds = int((piece_end - cursor).total_seconds())
                day = cursor.date()
                if day == today: today_seconds += seconds
                if week_start <= day <= today: week_seconds += seconds
                if day.isoformat() in daily: daily[day.isoformat()] += seconds
                cursor = piece_end
        for row in legacy:
            seconds = row["active_seconds"]
            day = datetime.fromisoformat(row["started_at"]).astimezone().date()
            total_seconds += seconds
            if day == today: today_seconds += seconds
            if week_start <= day <= today: week_seconds += seconds
            if day.isoformat() in daily: daily[day.isoformat()] += seconds
        return {"today_seconds": today_seconds, "week_seconds": week_seconds,
                "total_seconds": total_seconds, "daily": daily}

    def focus_action(self, action):
        if action not in ("pause", "resume", "stop"):
            raise ValueError("专注操作无效")
        self.focus_tick()
        with self.connect() as db:
            row = db.execute("SELECT * FROM focus_sessions WHERE status IN ('running','paused') ORDER BY started_at DESC LIMIT 1").fetchone()
            if not row:
                raise LookupError("没有正在进行的专注")
            status = "paused" if action == "pause" else "running" if action == "resume" else "finished"
            if action == "resume" and row["status"] != "paused" or action == "pause" and row["status"] != "running":
                raise ValueError("当前专注状态不支持此操作")
            now = utc_now()
            db.execute("UPDATE focus_sessions SET status=?,last_tick_at=?,ended_at=? WHERE id=?",
                       (status, now, now if action == "stop" else None, row["id"]))
            return dict(db.execute("SELECT * FROM focus_sessions WHERE id=?", (row["id"],)).fetchone())

    def focus_recover(self):
        with self.connect() as db:
            db.execute("UPDATE focus_sessions SET status='paused' WHERE status='running'")

    def settings(self):
        with self.connect() as db:
            return {r["key"]: r["value"] for r in db.execute("SELECT key,value FROM app_settings")}

    def update_settings(self, payload):
        allowed = {"reminders_paused", "course_lead_minutes", "task_lead_minutes", "display_name", "avatar_data"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError("设置字段无效")
        with self.connect() as db:
            for key, value in payload.items():
                if key == "reminders_paused":
                    if value not in (True, False, "true", "false"):
                        raise ValueError("提醒状态无效")
                    value = "true" if value in (True, "true") else "false"
                elif key in ("course_lead_minutes", "task_lead_minutes"):
                    value = int(value)
                    if not 0 <= value <= 10080:
                        raise ValueError("提前时间需在 0–10080 分钟之间")
                    value = str(value)
                elif key == "display_name":
                    value = required_text(value, "昵称", 30)
                else:
                    value = str(value or "")
                    if value and not value.startswith(("data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,")):
                        raise ValueError("头像图片格式无效")
                    if len(value) > 400_000:
                        raise ValueError("头像图片过大")
                db.execute("INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
        return self.settings()

    def claim_reminder(self, source_type, source_id, occurrence_key, lead_minutes, scheduled_at):
        with self.connect() as db:
            try:
                db.execute("INSERT INTO reminder_deliveries VALUES (?,?,?,?,?,?,?)",
                           (uid(), source_type, source_id, occurrence_key, lead_minutes, scheduled_at, utc_now()))
                return True
            except sqlite3.IntegrityError:
                return False

    def release_reminder(self, source_type, source_id, occurrence_key, lead_minutes, scheduled_at):
        with self.connect() as db:
            db.execute("""DELETE FROM reminder_deliveries WHERE source_type=? AND source_id=?
                          AND occurrence_key=? AND lead_minutes=? AND scheduled_at=?""",
                       (source_type, source_id, occurrence_key, lead_minutes, scheduled_at))
