"""Local life records and optional diary access password."""
import hashlib
import hmac
import json
import secrets
import time
import uuid
from datetime import date
from .store import utc_now


class LifeMixin:
    def diary_status(self):
        with self.connect() as db:
            return {"enabled": bool(db.execute("SELECT 1 FROM diary_security").fetchone())}

    def diary_authorize(self, token):
        if self.diary_status()["enabled"]:
            if getattr(self, "_diary_sessions", {}).get(token, 0) < time.monotonic():
                raise ValueError("日记已锁定，请输入密码打开")

    def diary_unlock(self, password):
        with self.connect() as db:
            row = db.execute("SELECT * FROM diary_security WHERE id=1").fetchone()
        if row:
            digest = hashlib.pbkdf2_hmac("sha256", str(password).encode(), bytes.fromhex(row["salt"]), 310000).hex()
            if not hmac.compare_digest(digest, row["password_hash"]):
                raise ValueError("密码不正确")
        token = secrets.token_urlsafe(32)
        sessions = {k: v for k, v in getattr(self, "_diary_sessions", {}).items() if v > time.monotonic()}
        sessions[token] = time.monotonic() + 1800
        self._diary_sessions = sessions
        return {"token": token}

    def diary_lock(self, token):
        getattr(self, "_diary_sessions", {}).pop(token, None)

    def diary_security(self, payload, token):
        self.diary_authorize(token)
        enabled = payload.get("enabled") is True
        password = str(payload.get("password", ""))
        if enabled and not 6 <= len(password) <= 128:
            raise ValueError("密码长度需为 6–128 个字符")
        with self.connect() as db:
            db.execute("DELETE FROM diary_security")
            if enabled:
                salt = secrets.token_bytes(16)
                digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000).hex()
                db.execute("INSERT INTO diary_security VALUES (1,?,?)", (salt.hex(), digest))
        self._diary_sessions = {}
        return {"enabled": enabled, **self.diary_unlock(password)}

    def life_records(self, kind, token="", payload=None, item_id=None, delete=False):
        if kind not in ("diary", "exercise", "coffee"):
            raise ValueError("生活模块不存在")
        if kind == "diary":
            self.diary_authorize(token)
        with self.connect() as db:
            if delete:
                if not db.execute("DELETE FROM life_entries WHERE id=? AND kind=?", (item_id, kind)).rowcount:
                    raise LookupError("记录不存在")
                return {"ok": True}
            if payload is not None:
                day = date.fromisoformat(str(payload.get("date", ""))).isoformat()
                title = str(payload.get("title", "")).strip()
                notes = str(payload.get("notes", "")).strip()
                if not title or len(title) > 120 or len(notes) > 20000:
                    raise ValueError("请填写标题（最多120字），正文最多20000字")
                clean = {"title": title, "notes": notes, "date": day}
                if kind == "exercise":
                    minutes = int(payload.get("minutes", 0))
                    if not 1 <= minutes <= 1440:
                        raise ValueError("运动时长需为1–1440分钟")
                    clean["minutes"] = minutes
                if kind == "coffee":
                    rating = int(payload.get("rating", 3))
                    if not 1 <= rating <= 5:
                        raise ValueError("评分需为1–5星")
                    clean["rating"] = rating
                if item_id:
                    if not db.execute("SELECT 1 FROM life_entries WHERE id=? AND kind=?", (item_id, kind)).fetchone():
                        raise LookupError("记录不存在")
                    db.execute("UPDATE life_entries SET entry_date=?,payload=?,updated_at=? WHERE id=?", (day, json.dumps(clean, ensure_ascii=False), utc_now(), item_id))
                else:
                    item_id = uuid.uuid4().hex
                    db.execute("INSERT INTO life_entries VALUES (?,?,?,?,?)", (item_id, kind, day, json.dumps(clean, ensure_ascii=False), utc_now()))
                return {"id": item_id, **clean}
            return [{"id": row["id"], **json.loads(row["payload"])} for row in db.execute("SELECT * FROM life_entries WHERE kind=? ORDER BY entry_date DESC,updated_at DESC", (kind,))]
