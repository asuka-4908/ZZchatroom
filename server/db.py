import os
import sqlite3
import time
import hashlib
import threading

_lock = threading.RLock()
_conn = None
_db_path = None

def _get_conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(_db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn

def init_db(db_path: str):
    global _db_path
    _db_path = db_path
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              nick TEXT UNIQUE NOT NULL,
              password_hash TEXT NOT NULL,
              salt TEXT NOT NULL,
              created_at INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              room TEXT NOT NULL,
              sender TEXT NOT NULL,
              type TEXT NOT NULL,
              content TEXT NOT NULL,
              ts INTEGER NOT NULL
            )
            """
        )
        conn.commit()

def _hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((salt + password).encode("utf-8")).hexdigest()

def create_user(nick: str, password: str) -> tuple[bool, str]:
    if not nick or not password:
        return False, "参数错误"
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE nick=?", (nick,))
        if cur.fetchone():
            return False, "昵称已存在"
        salt = os.urandom(16).hex()
        ph = _hash_password(password, salt)
        cur.execute(
            "INSERT INTO users(nick, password_hash, salt, created_at) VALUES(?,?,?,?)",
            (nick, ph, salt, int(time.time()))
        )
        conn.commit()
        return True, "注册成功"

def verify_user(nick: str, password: str) -> tuple[bool, str]:
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("SELECT password_hash, salt FROM users WHERE nick=?", (nick,))
        row = cur.fetchone()
        if not row:
            return False, "用户不存在"
        ph = _hash_password(password, row["salt"])
        if ph != row["password_hash"]:
            return False, "密码错误"
        return True, "登录成功"

def save_message(room: str, sender: str, mtype: str, content: str, ts: int):
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages(room, sender, type, content, ts) VALUES(?,?,?,?,?)",
            (room, sender, mtype, content, ts)
        )
        conn.commit()

def fetch_history(room: str, limit: int = 50, before_ts: int | None = None) -> list[dict]:
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        if before_ts is None:
            cur.execute(
                "SELECT room, sender, type, content, ts FROM messages WHERE room=? ORDER BY ts ASC LIMIT ?",
                (room, limit)
            )
        else:
            cur.execute(
                "SELECT room, sender, type, content, ts FROM messages WHERE room=? AND ts<? ORDER BY ts ASC LIMIT ?",
                (room, before_ts, limit)
            )
        rows = cur.fetchall()
        return [{"room": r["room"], "sender": r["sender"], "type": r["type"], "content": r["content"], "ts": r["ts"]} for r in rows]

def clear_history(room: str):
    with _lock:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM messages WHERE room=?", (room,))
        conn.commit()
