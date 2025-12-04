import json
import time
import tornado.httpclient

async def handle_bilibili(ws, content: str):
    url = ""
    try:
        parts = content.split()
        for i, p in enumerate(parts):
            if "📺b站视频" in p:
                if len(p) > 5:
                    url = p.replace("📺b站视频", "")
                elif i + 1 < len(parts):
                    url = parts[i+1]
                break
    except Exception:
        pass
    if not url:
        ws.broadcast({"type": "system", "content": "请提供B站视频链接，例如：📺b站视频 https://www.bilibili.com/video/BV...", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        return
    client = tornado.httpclient.AsyncHTTPClient()
    try:
        api_url = f"https://api.yujn.cn/api/blbl.php?url={url}"
        resp = await client.fetch(api_url)
        res = json.loads(resp.body)
        if res.get("code") == 1:
            video_data = res.get("data", [])
            video_url = ""
            if video_data and isinstance(video_data, list):
                video_url = video_data[0].get("video_url", "")
            if video_url:
                payload = {
                    "type": "bilibili_card",
                    "content": {
                        "src": video_url,
                        "title": res.get("title", "未知视频"),
                        "cover": res.get("imgurl", ""),
                        "desc": res.get("desc", "")
                    },
                    "ts": int(time.time() * 1000),
                    "sender": "ZZ机器人"
                }
                ws.broadcast(payload)
            else:
                ws.broadcast({"type": "system", "content": "解析成功但未获取到视频地址。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        else:
            msg = res.get("msg", "解析失败")
            ws.broadcast({"type": "system", "content": f"B站视频解析失败: {msg}", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
    except Exception as e:
        print(f"Bilibili API Error: {e}")
        ws.broadcast({"type": "system", "content": "B站视频解析服务暂时不可用。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})

