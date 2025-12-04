import json
import time
import tornado.httpclient

async def handle_weather(ws, content: str):
    city = ""
    try:
        if "[" in content and "]" in content:
            start = content.find("[")
            end = content.find("]")
            if start < end:
                c = content[start+1:end].strip()
                if c:
                    city = c
        else:
            parts = content.split()
            for i, p in enumerate(parts):
                if "⛅天气" in p:
                    if len(p) > 3:
                        city = p.replace("⛅天气", "").strip()
                    elif i + 1 < len(parts):
                        city = parts[i+1].strip()
                    break
    except Exception:
        pass
    if not city:
        ws.broadcast({"type": "system", "content": "请指定城市，例如：⛅天气[成都] 或 ⛅天气 成都", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        return
    client = tornado.httpclient.AsyncHTTPClient()
    try:
        api_key = "6a772ccc79edf696"
        url = f"https://v2.xxapi.cn/api/weatherDetails?city={city}&key={api_key}"
        req = tornado.httpclient.HTTPRequest(url=url, method="GET", headers={'User-Agent': 'xiaoxiaoapi/1.0.0'})
        resp = await client.fetch(req)
        res = json.loads(resp.body)
        if res.get("code") == 200:
            data = res.get("data", {})
            daily_data = data.get("data", [])
            if daily_data:
                today = daily_data[0]
                real_time = today.get("real_time_weather", [{}])[0] if today.get("real_time_weather") else {}
                payload = {
                    "type": "weather_card",
                    "content": {
                        "city": data.get("city"),
                        "date": today.get("date"),
                        "day": today.get("day"),
                        "weather": today.get("weather_from"),
                        "temp_range": f"{today.get('low_temp')}°C ~ {today.get('high_temp')}°C",
                        "current_temp": real_time.get("temperature", "N/A"),
                        "wind": f"{today.get('wind_from')} {today.get('wind_level_from')}",
                        "description": real_time.get("description", today.get("weather_from")),
                        "humidity": real_time.get("humidity", "")
                    },
                    "ts": int(time.time() * 1000),
                    "sender": "ZZ机器人"
                }
                ws.broadcast(payload)
            else:
                ws.broadcast({"type": "system", "content": f"未找到 {city} 的天气信息", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
        else:
            msg = res.get("msg", "未知错误")
            ws.broadcast({"type": "system", "content": f"天气查询失败: {msg}", "ts": int(time.time() * 1000), "sender": "ZZ系统"})
    except Exception as e:
        print(f"Weather API Error: {e}")
        ws.broadcast({"type": "system", "content": "天气服务暂时不可用", "ts": int(time.time() * 1000), "sender": "ZZ系统"})

