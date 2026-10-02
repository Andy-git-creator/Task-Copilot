"""Authenticated, per-workspace Windows named-pipe commands and process locks."""

from __future__ import annotations

import hashlib
import msvcrt
import os
import secrets
from multiprocessing.connection import Client, Listener
from pathlib import Path


def pipe_name(kind: str, data_dir: Path) -> str:
    digest = hashlib.sha256(str(data_dir.resolve()).lower().encode("utf-8")).hexdigest()[:16]
    return rf"\\.\pipe\TaskCopilot-{kind}-{digest}"


def authkey(data_dir: Path) -> bytes:
    path = data_dir / "ipc.key"
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as handle:
            handle.write(secrets.token_bytes(32))
    key = path.read_bytes()
    if len(key) != 32:
        raise RuntimeError("本地进程密钥无效")
    return key


class ProcessLock:
    def __init__(self, path: Path):
        self.file = open(path, "a+b")
        self.file.seek(0)
        try:
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            self.file.close()
            raise RuntimeError("进程已在运行")

    def close(self):
        try:
            self.file.seek(0)
            msvcrt.locking(self.file.fileno(), msvcrt.LK_UNLCK, 1)
        finally:
            self.file.close()


def send_command(kind: str, data_dir: Path, command: str) -> bool:
    try:
        connection = Client(pipe_name(kind, data_dir), family="AF_PIPE", authkey=authkey(data_dir))
        try:
            connection.send({"command": command})
            return connection.recv() == {"ok": True}
        finally:
            connection.close()
    except (OSError, EOFError, ConnectionError):
        return False


def serve_commands(kind: str, data_dir: Path, handler, stop_event):
    listener = Listener(pipe_name(kind, data_dir), family="AF_PIPE", authkey=authkey(data_dir))
    try:
        while not stop_event.is_set():
            try:
                connection = listener.accept()
            except (OSError, EOFError):
                if stop_event.is_set():
                    break
                continue
            try:
                message = connection.recv()
                allowed = isinstance(message, dict) and message.get("command") in ("ping", "show", "exit")
                if allowed:
                    handler(message["command"])
                connection.send({"ok": bool(allowed)})
            except (OSError, EOFError):
                pass
            finally:
                connection.close()
    finally:
        listener.close()
