import json
import time
import tornado.httpclient

async def handle_music(ws):
    client = tornado.httpclient.AsyncHTTPClient()
    try:
        url = "https://api.qqsuu.cn/api/dm-randmusic?sort=热歌榜&format=json"
        resp = await client.fetch(url)
        res = json.loads(resp.body)
        if res.get("code") in [1, 200]:
            d = res.get("data", {})
            name = d.get("name", "未知歌曲")
            singer = d.get("singer", d.get("artists_name", "未知歌手"))
            audio_url = d.get("url", "")
            cover_url = d.get("image", d.get("picurl", ""))
            if audio_url:
                payload = {
                    "type": "music_card",
                    "content": {
                        "name": name,
                        "singer": singer,
                        "url": audio_url,
                        "cover": cover_url
                    },
                    "ts": int(time.time() * 1000),
                    "sender": "ZZ机器人"
                }
                ws.broadcast(payload)
            else:
                ws.broadcast({"type": "system", "content": "抱歉，未能获取到音乐资源。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        else:
            ws.broadcast({"type": "system", "content": "音乐接口返回异常。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
    except Exception as e:
        print(f"Music API Error: {e}")
        ws.broadcast({"type": "system", "content": "音乐服务暂时不可用。", "ts": int(time.time() * 1000), "sender": "ZZ系统"})

