"""SQLite persistence for the first usable task module."""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


KINDS = {"general", "homework", "exam", "project"}
PRIORITIES = {"low", "medium", "high", "urgent"}
STATUSES = {"todo", "doing", "done"}


def data_path() -> Path:
    override = os.environ.get("TASK_COPILOT_DATA_DIR")
    root = Path(override) if override else Path(__file__).resolve().parent.parent / ".local-data"
    root.mkdir(parents=True, exist_ok=True)
    return root / "taskcopilot.db"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path: Path | None = None):
        self.path = path or data_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=5000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _migrate(self):
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY)")
            version = db.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations").fetchone()[0]
            if version > 7:
                raise RuntimeError("数据库版本高于当前程序支持的版本")
            if version == 0:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE tasks (
                        id TEXT PRIMARY KEY,
                        title TEXT NOT NULL CHECK(length(trim(title)) > 0),
                        description TEXT NOT NULL DEFAULT '',
                        kind TEXT NOT NULL CHECK(kind IN ('general','homework','exam','project')),
                        priority TEXT NOT NULL CHECK(priority IN ('low','medium','high','urgent')),
                        status TEXT NOT NULL CHECK(status IN ('todo','doing','done')),
                        due_at TEXT,
                        completed_at TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );
                    CREATE INDEX idx_tasks_due ON tasks(due_at);
                    CREATE INDEX idx_tasks_status ON tasks(status);
                    INSERT INTO schema_migrations(version) VALUES (1);
                    COMMIT;
                """)
                version = 1
            if version == 1:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE projects (
                        id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
                        status TEXT NOT NULL DEFAULT 'active', due_at TEXT,
                        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    ALTER TABLE tasks ADD COLUMN project_id TEXT REFERENCES projects(id) ON DELETE SET NULL;
                    CREATE INDEX idx_tasks_project ON tasks(project_id);
                    CREATE TABLE subtasks (
                        id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                        title TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0,
                        position INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE INDEX idx_subtasks_task ON subtasks(task_id, position);
                    CREATE TABLE terms (
                        id TEXT PRIMARY KEY, name TEXT NOT NULL, start_date TEXT NOT NULL,
                        weeks INTEGER NOT NULL, is_active INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE courses (
                        id TEXT PRIMARY KEY, term_id TEXT NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
                        name TEXT NOT NULL, teacher TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
                        color TEXT NOT NULL DEFAULT '#5c9394', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                    );
                    CREATE TABLE course_rules (
                        id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                        weekday INTEGER NOT NULL, start_time TEXT NOT NULL, end_time TEXT NOT NULL,
                        start_week INTEGER NOT NULL, end_week INTEGER NOT NULL, week_type TEXT NOT NULL DEFAULT 'all'
                    );
                    CREATE TABLE course_exceptions (
                        id TEXT PRIMARY KEY, course_id TEXT NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                        rule_id TEXT REFERENCES course_rules(id) ON DELETE CASCADE,
                        original_date TEXT, action TEXT NOT NULL, target_date TEXT,
                        start_time TEXT, end_time TEXT, location TEXT, teacher TEXT, created_at TEXT NOT NULL
                    );
                    CREATE UNIQUE INDEX idx_course_exception_original ON course_exceptions(rule_id, original_date) WHERE rule_id IS NOT NULL;
                    CREATE INDEX idx_course_exception_target ON course_exceptions(target_date);
                    CREATE TABLE focus_sessions (
                        id TEXT PRIMARY KEY, task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
                        project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
                        started_at TEXT NOT NULL, ended_at TEXT, last_tick_at TEXT NOT NULL,
                        active_seconds INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL
                    );
                    CREATE INDEX idx_focus_started ON focus_sessions(started_at);
                    CREATE TABLE reminder_deliveries (
                        id TEXT PRIMARY KEY, source_type TEXT NOT NULL, source_id TEXT NOT NULL,
                        occurrence_key TEXT NOT NULL, lead_minutes INTEGER NOT NULL,
                        scheduled_at TEXT NOT NULL, sent_at TEXT NOT NULL,
                        UNIQUE(source_type,source_id,occurrence_key,lead_minutes,scheduled_at)
                    );
                    CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                    INSERT INTO app_settings(key,value) VALUES ('reminders_paused','false'),('course_lead_minutes','10'),('task_lead_minutes','60');
                    INSERT INTO schema_migrations(version) VALUES (2);
                    COMMIT;
                """)
                version = 2
            if version == 2:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE focus_segments (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL REFERENCES focus_sessions(id) ON DELETE CASCADE,
                        started_at TEXT NOT NULL,
                        ended_at TEXT NOT NULL,
                        effective_seconds INTEGER NOT NULL
                    );
                    CREATE INDEX idx_focus_segments_time ON focus_segments(started_at, ended_at);
                    INSERT INTO schema_migrations(version) VALUES (3);
                    COMMIT;
                """)
                version = 3
            if version == 3:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    INSERT OR IGNORE INTO app_settings(key,value) VALUES ('display_name','Task Copilot 用户');
                    INSERT OR IGNORE INTO app_settings(key,value) VALUES ('avatar_data','');
                    INSERT INTO schema_migrations(version) VALUES (4);
                    COMMIT;
                """)
                version = 4
            if version == 4:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    ALTER TABLE course_exceptions ADD COLUMN active INTEGER NOT NULL DEFAULT 1;
                    DROP INDEX idx_course_exception_original;
                    CREATE UNIQUE INDEX idx_course_exception_original ON course_exceptions(rule_id, original_date) WHERE rule_id IS NOT NULL AND active=1;
                    INSERT INTO schema_migrations(version) VALUES (5);
                    COMMIT;
                """)
                version = 5
            if version == 5:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    ALTER TABLE course_exceptions ADD COLUMN record_visible INTEGER NOT NULL DEFAULT 1;
                    INSERT INTO schema_migrations(version) VALUES (6);
                    COMMIT;
                """)
                version = 6
            if version == 6:
                db.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE life_entries(id TEXT PRIMARY KEY,kind TEXT NOT NULL,entry_date TEXT NOT NULL,payload TEXT NOT NULL,updated_at TEXT NOT NULL);
                    CREATE INDEX idx_life_entries ON life_entries(kind,entry_date);
                    CREATE TABLE diary_security(id INTEGER PRIMARY KEY CHECK(id=1),salt TEXT NOT NULL,password_hash TEXT NOT NULL);
                    INSERT INTO schema_migrations(version) VALUES (7);
                    COMMIT;
                """)

    def list_tasks(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("""
                SELECT tasks.*,
                    (SELECT COUNT(*) FROM subtasks WHERE task_id=tasks.id) AS subtask_total,
                    (SELECT COUNT(*) FROM subtasks WHERE task_id=tasks.id AND done=1) AS subtask_done
                FROM tasks
                ORDER BY CASE status WHEN 'done' THEN 1 ELSE 0 END,
                         CASE WHEN due_at IS NULL THEN 1 ELSE 0 END,
                         due_at ASC,
                         CASE priority WHEN 'urgent' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                         created_at DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def create_task(self, payload: dict) -> dict:
        title = str(payload.get("title", "")).strip()
        if not title or len(title) > 120:
            raise ValueError("任务标题需为 1–120 个字符")
        description = str(payload.get("description", "")).strip()
        if len(description) > 1000:
            raise ValueError("描述不能超过 1000 个字符")
        kind = payload.get("kind", "general")
        priority = payload.get("priority", "medium")
        if kind not in KINDS or priority not in PRIORITIES:
            raise ValueError("任务类别或优先级无效")
        due_at = self._validate_due(payload.get("due_at"))
        project_id = payload.get("project_id") or None
        item_id, now = uuid.uuid4().hex, utc_now()
        with self.connect() as db:
            if project_id and not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("项目不存在")
            db.execute("""
                INSERT INTO tasks(id,title,description,kind,priority,status,due_at,completed_at,created_at,updated_at,project_id)
                VALUES (?,?,?,?,?,'todo',?,NULL,?,?,?)
            """, (item_id, title, description, kind, priority, due_at, now, now, project_id))
            return dict(db.execute("SELECT * FROM tasks WHERE id=?", (item_id,)).fetchone())

    def update_task(self, task_id: str, payload: dict) -> dict:
        allowed = {"title", "description", "kind", "priority", "due_at", "status", "project_id"}
        if not isinstance(payload, dict) or not payload or set(payload) - allowed:
            raise ValueError("任务字段无效")
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
            if not row:
                raise LookupError("任务不存在")
            item = dict(row)
            item.update(payload)
            title = str(item["title"]).strip()
            description = str(item["description"]).strip()
            if not title or len(title) > 120 or len(description) > 1000:
                raise ValueError("标题或描述长度无效")
            if item["kind"] not in KINDS or item["priority"] not in PRIORITIES or item["status"] not in STATUSES:
                raise ValueError("任务状态、类别或优先级无效")
            due_at = self._validate_due(item["due_at"])
            project_id = item["project_id"] or None
            if project_id and not db.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise ValueError("项目不存在")
            completed_at = item["completed_at"]
            if item["status"] == "done" and row["status"] != "done":
                completed_at = utc_now()
            elif item["status"] != "done":
                completed_at = None
            db.execute("""
                UPDATE tasks SET title=?,description=?,kind=?,priority=?,status=?,due_at=?,completed_at=?,updated_at=?,project_id=?
                WHERE id=?
            """, (title, description, item["kind"], item["priority"], item["status"], due_at, completed_at, utc_now(), project_id, task_id))
            if item["status"] == "done" and row["status"] != "done":
                db.execute("UPDATE subtasks SET done=1,updated_at=? WHERE task_id=? AND done=0", (utc_now(), task_id))
            return dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())

    def delete_task(self, task_id: str) -> None:
        with self.connect() as db:
            if db.execute("DELETE FROM tasks WHERE id=?", (task_id,)).rowcount == 0:
                raise LookupError("任务不存在")

    @staticmethod
    def _validate_due(raw) -> str | None:
        if raw in (None, ""):
            return None
        if not isinstance(raw, str):
            raise ValueError("截止时间格式无效")
        try:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("截止时间格式无效") from exc
        if value.tzinfo is None:
            raise ValueError("截止时间必须包含时区")
        return value.astimezone(timezone.utc).isoformat(timespec="seconds")
