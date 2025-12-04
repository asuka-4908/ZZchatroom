import json
import time
import tornado.httpclient

async def handle_news(ws):
    client = tornado.httpclient.AsyncHTTPClient()
    try:
        url = "https://api.yujn.cn/api/new.php"
        req = tornado.httpclient.HTTPRequest(url=url, method="GET", headers={"User-Agent": "xiaoxiaoapi/1.0.0"})
        resp = await client.fetch(req)
        res = json.loads(resp.body)
        if res.get("code") == 200:
            items = res.get("data", [])
            if not isinstance(items, list):
                items = []
            items = items[:5]
            payload = {
                "type": "news_card",
                "content": items,
                "ts": int(time.time() * 1000),
                "sender": "ZZ机器人"
            }
            ws.broadcast(payload)
        else:
            msg = res.get("msg", "新闻接口返回异常")
            ws.broadcast({"type": "system", "content": f"新闻获取失败: {msg}", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
    except Exception as e:
        print(f"News API Error: {e}")
        ws.broadcast({"type": "system", "content": "新闻服务暂时不可用。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})

