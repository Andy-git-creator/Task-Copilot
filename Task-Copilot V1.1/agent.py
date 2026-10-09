"""Independent user-session reminder and tray process."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
from winotify import Notification, audio

from backend.features import FeatureStore
from backend.ipc import ProcessLock, send_command, serve_commands


def icon_image():
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((4, 4, 60, 60), radius=16, fill="#3d7980")
    draw.line((19, 33, 28, 42, 47, 22), fill="white", width=7, joint="curve")
    return image


class Agent:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = FeatureStore(data_dir / "taskcopilot.db")
        self.store.movement_startup()
        self.stop = threading.Event()
        self.log = logging.getLogger("taskcopilot.agent")
        self.icon = pystray.Icon("Task Copilot", icon_image(), "Task Copilot", menu=pystray.Menu(
            pystray.MenuItem("打开主界面", self.open_desktop, default=True),
            pystray.MenuItem(lambda item: "恢复提醒" if self.store.settings()["reminders_paused"] == "true" else "暂停提醒", self.toggle_pause),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.quit),
        ))

    def open_desktop(self, *_):
        if send_command("desktop", self.data_dir, "show"):
            return
        root = Path(__file__).resolve().parent
        python = Path(sys.executable).with_name("pythonw.exe")
        executable = str(python if python.exists() else sys.executable)
        try:
            subprocess.Popen([executable, str(root / "start.pyw")], cwd=root, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            self.log.exception("Cannot open desktop")

    def toggle_pause(self, *_):
        current = self.store.settings()["reminders_paused"] == "true"
        self.store.update_settings({"reminders_paused": not current})
        self.icon.update_menu()

    def quit(self, *_):
        self.stop.set()
        send_command("desktop", self.data_dir, "exit")
        self.icon.stop()

    def command(self, command):
        if command == "show":
            self.open_desktop()
        elif command == "exit":
            self.quit()

    def run(self):
        threading.Thread(target=serve_commands, args=("agent", self.data_dir, self.command, self.stop), daemon=True).start()
        threading.Thread(target=self.reminder_loop, daemon=True).start()
        self.icon.run()
        self.stop.set()

    def reminder_loop(self):
        while not self.stop.is_set():
            try:
                self.scan_reminders()
            except Exception:
                self.log.exception("Reminder scan failed")
            self.stop.wait(15)

    def scan_reminders(self, now=None, notify=None):
        now = now or datetime.now(timezone.utc)
        settings = self.store.settings()
        if settings["reminders_paused"] == "true":
            return 0
        notify = notify or self.show_notification
        candidates = []
        task_leads = settings["task_reminder_minutes"]
        lead_course = int(settings["course_lead_minutes"])
        for task in self.store.list_tasks():
            if task["status"] == "done" or not task["due_at"]:
                continue
            event = datetime.fromisoformat(task["due_at"])
            for lead_task in task_leads:
                candidates.append(("task", task["id"], task["id"], lead_task, event, "任务即将截止", task["title"]))
        local_now = now.astimezone()
        start = local_now.date()
        end = start + timedelta(days=3)
        for course in self.store.occurrences(start.isoformat(), end.isoformat()):
            local_event = datetime.fromisoformat(f"{course['date']}T{course['start_time']}:00").astimezone()
            candidates.append(("course", course["course_id"], course["occurrence_key"], lead_course,
                               local_event.astimezone(timezone.utc), "即将上课", f"{course['name']} · {course['location'] or '地点待定'}"))
        count = 0
        for source_type, source_id, key, lead, event, title, message in candidates:
            trigger = event - timedelta(minutes=lead)
            if not trigger <= now <= trigger + timedelta(minutes=15):
                continue
            scheduled = event.isoformat(timespec="seconds")
            if not self.store.claim_reminder(source_type, source_id, key, lead, scheduled):
                continue
            try:
                notify(title, message)
                count += 1
            except Exception:
                self.store.release_reminder(source_type, source_id, key, lead, scheduled)
                self.log.exception("Notification failed")
        try:
            count += self.store.movement_scan(now, notify)
        except Exception:
            self.log.exception("Movement reminder failed")
        return count

    @staticmethod
    def show_notification(title, message):
        toast = Notification(app_id="Task Copilot", title=title, msg=message, duration="short")
        toast.set_audio(audio.Default, loop=False)
        toast.show()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    data_dir = args.data_dir.resolve()
    data_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=data_dir / "agent.log", level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    try:
        lock = ProcessLock(data_dir / "agent.lock")
    except RuntimeError:
        return
    try:
        Agent(data_dir).run()
    finally:
        lock.close()


if __name__ == "__main__":
    main()
