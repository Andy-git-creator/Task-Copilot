"""Run the packaged web frontend with the local Python backend."""

from __future__ import annotations

import argparse
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

from backend.server import AppServer
from backend.features import FeatureStore
from backend.ipc import ProcessLock, send_command, serve_commands


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", action="store_true", help="在系统浏览器打开，便于开发调试")
    parser.add_argument("--serve", action="store_true", help="只启动本地服务，便于检查前端")
    args = parser.parse_args()

    assets = Path(__file__).resolve().parent / "frontend" / "dist"
    if not (assets / "index.html").exists():
        raise SystemExit("前端尚未构建。请先运行：cd frontend && npm install && npm run build")
    store = FeatureStore()
    data_dir = store.path.parent
    desktop_lock = None
    quit_requested = threading.Event()
    if not (args.browser or args.serve):
        try:
            desktop_lock = ProcessLock(data_dir / "desktop.lock")
        except RuntimeError:
            send_command("desktop", data_dir, "show")
            return
        if not send_command("agent", data_dir, "ping"):
            python = Path(sys.executable).with_name("pythonw.exe")
            executable = str(python if python.exists() else sys.executable)
            subprocess.Popen([executable, str(Path(__file__).resolve().parent / "agent.py"), "--data-dir", str(data_dir)],
                             cwd=Path(__file__).resolve().parent, creationflags=subprocess.CREATE_NO_WINDOW)
            for _ in range(40):
                if send_command("agent", data_dir, "ping"):
                    break
                time.sleep(0.25)
            else:
                desktop_lock.close()
                raise SystemExit("后台托盘进程未能启动，请检查数据目录中的 agent.log")
    store.focus_recover()
    server = AppServer(("127.0.0.1", 0), store, secrets.token_urlsafe(32), assets)
    threading.Thread(target=server.serve_forever, name="task-http", daemon=True).start()
    def focus_heartbeat():
        while True:
            store.focus_tick()
            threading.Event().wait(5)
    threading.Thread(target=focus_heartbeat, name="focus-heartbeat", daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/?token={quote(server.token)}"
    try:
        if args.browser or args.serve:
            import webbrowser
            if args.browser:
                webbrowser.open(url)
            print(f"Task Copilot 已启动：{url}\n按 Ctrl+C 退出")
            threading.Event().wait()
        else:
            try:
                import webview
            except ImportError as exc:
                raise SystemExit("缺少 pywebview。请安装 requirements.txt，或使用 --browser 调试模式") from exc
            window = webview.create_window("Task Copilot", url, width=1360, height=900, min_size=(960, 640), background_color="#f7f8fa")
            def closing():
                if quit_requested.is_set():
                    return
                window.hide()
                return False
            def desktop_command(command):
                if command == "show":
                    window.show()
                    window.restore()
                elif command == "exit":
                    quit_requested.set()
                    window.destroy()
            window.events.closing += closing
            threading.Thread(target=serve_commands, args=("desktop", data_dir, desktop_command, quit_requested), daemon=True).start()
            webview.start(gui="edgechromium")
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        server.server_close()
        if desktop_lock:
            desktop_lock.close()


if __name__ == "__main__":
    main()
