import json
import os
import sys
import time
from urllib.parse import urlencode

import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.httpclient
import tornado.escape
from db import init_db, create_user, verify_user, save_message, fetch_history, clear_history
from plugins.music import handle_music as plugin_handle_music
from plugins.weather import handle_weather as plugin_handle_weather
from plugins.movie import handle_movie as plugin_handle_movie
from plugins.bilibili import handle_bilibili as plugin_handle_bilibili
from plugins.news import handle_news as plugin_handle_news
from plugins.ai import build_system_prompt


ROOMS = {}


def get_room(room_id: str):
    if room_id not in ROOMS:
        ROOMS[room_id] = {
            "clients": set(),
        }
    return ROOMS[room_id]


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        self.redirect("/login")


class LoginPageHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("login.html")


class ChatPageHandler(tornado.web.RequestHandler):
    def get(self):
        nick_cookie = self.get_secure_cookie("nick")
        nick = self.get_argument("nick", None) or (nick_cookie.decode("utf-8") if nick_cookie else None)
        server = self.get_argument("server", None)
        room = self.get_argument("room", "general")
        if not nick or not server:
            self.redirect("/login")
            return
        self.render("chat.html", nick=nick, server=server, room=room)


class ConfigHandler(tornado.web.RequestHandler):
    def get(self):
        base_dir = get_base_dir()
        exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        candidates = [
            os.path.join(exe_dir, "config", "config.json"),
            os.path.join(exe_dir, "config.json"),
            os.path.join(base_dir, "config", "config.json"),
            os.path.join(os.path.dirname(__file__), "..", "config", "config.json"),
        ]
        config_path = None
        for p in candidates:
            if os.path.exists(p):
                config_path = p
                break
        try:
            if config_path:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                raise FileNotFoundError()
        except Exception:
            data = {
                "servers": [
                    {
                        "name": "当前访问域",
                        "ws_url": f"{'wss' if self.request.protocol == 'https' else 'ws'}://{self.request.host}/ws",
                    }
                ]
            }
        else:
            try:
                dyn_url = f"{'wss' if self.request.protocol == 'https' else 'ws'}://{self.request.host}/ws"
                servers = data.get("servers") or []
                if not any(isinstance(s, dict) and s.get("ws_url") == dyn_url for s in servers):
                    servers.insert(0, {"name": "当前访问域", "ws_url": dyn_url})
                    data["servers"] = servers
            except Exception:
                pass
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps(data, ensure_ascii=False))


class HistoryHandler(tornado.web.RequestHandler):
    def get(self):
        room = self.get_argument("room", "general")
        limit = int(self.get_argument("limit", "50"))
        before = self.get_argument("before_ts", None)
        before_ts = int(before) if before else None
        order = self.get_argument("order", "desc").lower()
        items = fetch_history(room, limit, before_ts)
        if order == "desc":
            items = sorted(items, key=lambda x: x.get("ts", 0), reverse=True)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps({"items": items}, ensure_ascii=False))

class RegisterApiHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body or b"{}")
        except Exception:
            data = {}
        nick = str(data.get("nick", "")).strip()
        password = str(data.get("password", "")).strip()
        ok, msg = create_user(nick, password)
        code = 0 if ok else 1
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps({"code": code, "message": msg}, ensure_ascii=False))

class LoginApiHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body or b"{}")
        except Exception:
            data = {}
        nick = str(data.get("nick", "")).strip()
        password = str(data.get("password", "")).strip()
        ok, msg = verify_user(nick, password)
        if ok:
            self.set_secure_cookie("nick", nick)
        code = 0 if ok else 1
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps({"code": code, "message": msg}, ensure_ascii=False))

class ClearHistoryHandler(tornado.web.RequestHandler):
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body or b"{}")
        except Exception:
            data = {}
        room = str(data.get("room", "general")).strip() or "general"
        try:
            clear_history(room)
            code, msg = 0, "已清空"
        except Exception as e:
            code, msg = 1, str(e)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        self.finish(json.dumps({"code": code, "message": msg}, ensure_ascii=False))


class AIStreamHandler(tornado.web.RequestHandler):
    async def get(self):
        api_key = os.environ.get("SILICONFLOW_API_KEY")
        
        # 尝试从配置文件读取 API Key
        if not api_key:
            try:
                base_dir = get_base_dir()
                exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                candidates = [
                    os.path.join(exe_dir, "config", "config.json"),
                    os.path.join(exe_dir, "config.json"),
                    os.path.join(base_dir, "config", "config.json"),
                    os.path.join(os.path.dirname(__file__), "..", "config", "config.json"),
                ]
                for p in candidates:
                    if os.path.exists(p):
                        with open(p, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            api_key = data.get("siliconflow_api_key")
                        if api_key:
                            break
            except Exception:
                pass

        model = os.environ.get("SILICONFLOW_MODEL", "Qwen/Qwen2.5-7B-Instruct")
        base_url = os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1/")
        prompt = self.get_argument("prompt", "")
        if not api_key:
            self.set_header("Content-Type", "text/event-stream")
            self.write("event: error\n")
            self.write("data: API密钥未设置，请在环境变量SILICONFLOW_API_KEY或配置文件config.json中配置siliconflow_api_key\n\n")
            await self.flush()
            return
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.set_header("Connection", "keep-alive")

        body = json.dumps({
            "model": model,
            "stream": True,
            "messages": [
                {
                    "role": "system",
                    "content": build_system_prompt()
                },
                {"role": "user", "content": prompt}
            ]
        }, ensure_ascii=False).encode("utf-8")

        url = base_url.rstrip("/") + "/chat/completions"
        client = tornado.httpclient.AsyncHTTPClient()

        def streamer(chunk: bytes):
            try:
                self.write(chunk.decode("utf-8", errors="ignore"))
                tornado.ioloop.IOLoop.current().spawn_callback(self.flush)
            except Exception:
                pass

        req = tornado.httpclient.HTTPRequest(
            url=url,
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            body=body,
            request_timeout=300,
            streaming_callback=streamer,
        )
        try:
            await client.fetch(req)
        except Exception as e:
            msg = str(e).replace("\n", " ")
            self.write(f"event: error\ndata: {msg}\n\n")
            await self.flush()
        finally:
            self.write("data: [DONE]\n\n")
            await self.flush()


def make_system_message(content: str):
    return {
        "type": "system",
        "content": content,
        "ts": int(time.time() * 1000),
        "sender": "ZZ系统",
    }


def make_user_message(nick: str, content: str):
    return {
        "type": "message",
        "content": content,
        "ts": int(time.time() * 1000),
        "sender": nick,
    }


def make_bot_reply(trigger: str):
    replies = {
        "🤖成小理": "🤖成小理 功能接口已预留，正在建设中…",
        "🎵音乐": "正在处理 🎵音乐 请求… 🎵",
        "🎬电影": "正在处理 🎬电影 请求… 🎬",
        "⛅天气": "正在处理 ⛅天气 请求… ⛅",
        "📰新闻": "正在处理 📰新闻 请求… 📰",
        "📺b站视频": "正在处理 📺b站视频 请求… ▶️",
    }
    return {
        "type": "message",
        "content": replies.get(trigger, "功能接口已预留，正在建设中…"),
        "ts": int(time.time() * 1000),
        "sender": "ZZ机器人",
    }


class ChatWebSocket(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True

    def open(self):
        room = self.get_argument("room", "general")
        nick = self.get_argument("nick", "匿名用户")
        self.room_id = room
        self.nick = nick
        room_obj = get_room(room)
        room_obj["clients"].add(self)

        join_msg = make_system_message(f"{nick} 加入了房间 {room}")
        self.broadcast(join_msg)

    async def on_message(self, message):
        try:
            data = json.loads(message)
        except Exception:
            data = {"content": message}

        content = str(data.get("content", "")).strip()
        if not content:
            return

        msg = make_user_message(self.nick, content)
        self.broadcast(msg)

        if "🎵音乐" in content:
            await plugin_handle_music(self)
        elif "⛅天气" in content:
            await plugin_handle_weather(self, content)
        elif "🎬电影" in content:
            await plugin_handle_movie(self, content)
        elif "📰新闻" in content:
            await plugin_handle_news(self)
        elif "📺b站视频" in content:
            await plugin_handle_bilibili(self, content)
        else:
            triggers = ["🎵音乐", "🎬电影", "⛅天气", "📰新闻", "📺b站视频"]
            for t in triggers:
                if t in content:
                    self.broadcast(make_bot_reply(t))
                    break

    async def handle_bilibili(self, content):
        await plugin_handle_bilibili(self, content)

    async def handle_movie(self, content):
        await plugin_handle_movie(self, content)

    async def handle_weather(self, content):
        await plugin_handle_weather(self, content)

    async def handle_music(self):
        await plugin_handle_music(self)

    async def handle_news(self):
        await plugin_handle_news(self)

    def on_close(self):
        room_obj = get_room(self.room_id)
        room_obj["clients"].discard(self)
        leave_msg = make_system_message(f"{self.nick} 离开了房间 {self.room_id}")
        self.broadcast(leave_msg)

    def broadcast(self, payload: dict):
        room_obj = get_room(self.room_id)
        msg = json.dumps(payload, ensure_ascii=False)
        for client in list(room_obj["clients"]):
            try:
                client.write_message(msg)
            except Exception:
                pass
        try:
            mtype = str(payload.get("type", "message"))
            sender = str(payload.get("sender", ""))
            ts = int(payload.get("ts", int(time.time() * 1000)))
            content = payload.get("content", "")
            if isinstance(content, (dict, list)):
                content_text = json.dumps(content, ensure_ascii=False)
            else:
                content_text = str(content)
            save_message(self.room_id, sender, mtype, content_text, ts)
        except Exception:
            pass


def get_base_dir():
    import sys
    return getattr(sys, "_MEIPASS", os.path.dirname(__file__))


def make_app():
    base_dir = get_base_dir()
    templates_dir_candidates = [
        os.path.join(base_dir, "server", "templates"),
        os.path.join(base_dir, "templates"),
        os.path.join(os.path.dirname(__file__), "templates"),
    ]
    static_dir_candidates = [
        os.path.join(base_dir, "server", "static"),
        os.path.join(base_dir, "static"),
        os.path.join(os.path.dirname(__file__), "static"),
    ]
    favicon_dir_candidates = [
        os.path.join(base_dir, "favicon"),
        os.path.join(os.path.dirname(__file__), "..", "favicon"),
    ]
    def pick_path(cands):
        for p in cands:
            if os.path.isdir(p):
                return p
        return cands[-1]

    templates_dir = pick_path(templates_dir_candidates)
    static_dir = pick_path(static_dir_candidates)
    icon_dir = pick_path(favicon_dir_candidates)

    return tornado.web.Application(
        [
            (r"/", IndexHandler),
            (r"/login", LoginPageHandler),
            (r"/api/register", RegisterApiHandler),
            (r"/api/login", LoginApiHandler),
            (r"/chat", ChatPageHandler),
            (r"/favicon/(.*)", tornado.web.StaticFileHandler, {"path": icon_dir}),
            (r"/favicon.ico", tornado.web.StaticFileHandler, {"path": icon_dir, "default_filename": "favicon.ico"}),
            (r"/config", ConfigHandler),
            (r"/history", HistoryHandler),
            (r"/api/clear_history", ClearHistoryHandler),
            (r"/ai", AIStreamHandler),
            (r"/ws", ChatWebSocket),
        ],
        template_path=templates_dir,
        static_path=static_dir,
        debug=True,
        cookie_secret=os.environ.get("COOKIE_SECRET", "ZZCHAT_SECRET"),
    )


if __name__ == "__main__":
    base_dir = get_base_dir()
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    data_dir_candidates = [
        os.path.join(exe_dir, "data"),
        os.path.join(base_dir, "data"),
        os.path.join(os.path.dirname(__file__), "..", "data"),
    ]
    def pick_dir(cands):
        for p in cands:
            try:
                os.makedirs(p, exist_ok=True)
                return p
            except Exception:
                pass
        return cands[-1]
    data_dir = pick_dir(data_dir_candidates)
    db_path = os.path.join(data_dir, "zzchat.db")
    init_db(db_path)
    app = make_app()
    port = int(os.environ.get("PORT", "8891"))
    app.listen(port)
    print(f"ZZ聊天室 服务已启动: http://127.0.0.1:{port}/")
    tornado.ioloop.IOLoop.current().start()
