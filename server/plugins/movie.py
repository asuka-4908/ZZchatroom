import time

async def handle_movie(ws, content: str):
    url = ""
    try:
        parts = content.split()
        for i, p in enumerate(parts):
            if "🎬电影" in p:
                if len(p) > 3:
                    url = p.replace("🎬电影", "")
                elif i + 1 < len(parts):
                    url = parts[i+1]
                break
    except Exception:
        pass
    if not url:
        ws.broadcast({"type": "system", "content": "请提供电影链接，例如：🎬电影 https://...", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        return
    iframe_src = f"https://jx.2s0.cn/player/?url={url}"
    payload = {
        "type": "movie_card",
        "content": {
            "src": iframe_src,
            "original_url": url
        },
        "ts": int(time.time() * 1000),
        "sender": "ZZ机器人"
    }
    ws.broadcast(payload)

