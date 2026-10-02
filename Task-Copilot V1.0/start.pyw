"""Windowed launcher with a readable startup error log."""

import ctypes
import os
import traceback
from pathlib import Path

from app import main


if __name__ == "__main__":
    try:
        main()
    except Exception:
        data_dir = Path(os.environ.get("TASK_COPILOT_DATA_DIR") or Path(__file__).resolve().parent / ".local-data")
        data_dir.mkdir(parents=True, exist_ok=True)
        log = data_dir / "desktop.log"
        log.write_text(traceback.format_exc(), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(None, f"Task Copilot 启动失败。\n详情：{log}", "Task Copilot", 0x10)
