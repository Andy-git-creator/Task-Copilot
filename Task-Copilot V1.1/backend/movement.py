"""Timestamp based movement reminders, scanned by the tray process."""
from datetime import datetime, timedelta, timezone


class MovementMixin:
    @staticmethod
    def movement_write(db, key, value):
        db.execute("INSERT INTO app_settings(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

    def movement_startup(self, now=None):
        now = now or datetime.now(timezone.utc)
        with self.connect() as db:
            anchor = now.isoformat(timespec="seconds")
            self.movement_write(db, "_movement_anchor", anchor)
            self.movement_write(db, "_movement_last_notice", "")

    def movement_focus_start(self, db, now):
        self.movement_write(db, "_movement_anchor", now)
        self.movement_write(db, "_movement_last_notice", "")

    def movement_focus_stop(self, db, now):
        row = db.execute("SELECT value FROM app_settings WHERE key='_movement_last_notice'").fetchone()
        last = datetime.fromisoformat(row["value"]) if row and row["value"] else datetime.fromisoformat(now)
        self.movement_write(db, "_movement_anchor", (last + timedelta(minutes=10)).isoformat(timespec="seconds"))

    def movement_scan(self, now, notify):
        settings = self.settings()
        if settings["movement_enabled"] != "true" or settings["reminders_paused"] == "true":
            return 0
        with self.connect() as db:
            row = db.execute("SELECT value FROM app_settings WHERE key='_movement_anchor'").fetchone()
        if not row or not row["value"]:
            self.movement_startup(now)
            return 0
        anchor = datetime.fromisoformat(row["value"])
        interval = int(settings["movement_interval_minutes"])
        if now < anchor + timedelta(minutes=interval):
            return 0
        notify("起来活动一下", f"已经过去 {interval} 分钟了，起身走走、伸展一下，让身体休息片刻。")
        with self.connect() as db:
            stamp = now.isoformat(timespec="seconds")
            self.movement_write(db, "_movement_anchor", stamp)
            self.movement_write(db, "_movement_last_notice", stamp)
        return 1
