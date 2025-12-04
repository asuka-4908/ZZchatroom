# ZZ聊天室 项目说明

## 关键概览
- 单端口后端：HTTP、静态资源、SSE、WebSocket 统一由同一服务提供
- 默认端口为 `8889`，可通过环境变量 `PORT` 修改（示例使用 `8891`）
- AI 对话：代理硅基流 Chat API，SSE 流式返回到前端 `EventSource`

## 路由与协议
- HTTP 路由：`/login` 登录页、`/chat` 聊天页、`/config` 服务列表、`/ai` SSE 接口、`/favicon/*` 静态资源
- SSE：`/ai?prompt=...` 返回 `text/event-stream`，用于 AI 流式回复
- WebSocket：`ws://<你的域名或本地地址>/ws`，用于群聊消息推送

## 目录结构
- `server/app.py` Tornado 后端（路由、SSE、WebSocket）
- `server/templates/login.html` 登录页
- `server/templates/chat.html` 聊天页（WebSocket 消息、SSE 流式 AI）
- `server/static/vendor/jquery-3.7.1.min.js` 本地 jQuery 文件（CDN 自动回退）
- `config/config.json` 外网 WS 地址配置

## 启动方法（Windows PowerShell）
1. 创建虚拟环境并安装依赖（若已存在可跳过）
   ```powershell
   python -m venv venv
   .\venv\Scripts\pip install tornado
   ```
2. 设置环境变量并启动服务（端口可按需调整）
   ```powershell
   $env:PORT=8891
   $env:SILICONFLOW_API_KEY="<你的Key>"
   $env:SILICONFLOW_MODEL="Qwen/Qwen2.5-7B-Instruct"
   $env:SILICONFLOW_BASE_URL="https://api.siliconflow.cn/v1/"
   .\venv\Scripts\python server\app.py
   ```
3. 访问本地入口
   - `http://127.0.0.1:8891/login`

## 配置方法
- WebSocket 地址在 `config/config.json` 中配置示例：
  ```json
  {
    "servers": [
      {
        "name": "本地服务器",
        "ws_url": "ws://ngrok.xiaomiqiu123.top:63373/ws"
      }
    ]
  }
  ```
- 若使用 HTTPS 隧道统一域名，可改为 `wss://<你的域名>/ws`
- 前端资源：jQuery 本地优先、CDN 回退；本地路径为 `/static/vendor/jquery-3.7.1.min.js`
- AI 相关环境变量：
  - `SILICONFLOW_API_KEY`：硅基流 API Key
  - `SILICONFLOW_MODEL`：模型名，默认 `Qwen/Qwen2.5-7B-Instruct`
  - `SILICONFLOW_BASE_URL`：默认 `https://api.siliconflow.cn/v1/`

## 使用说明（聊天指令）
- `🤖成小理`：在消息中包含此标签可触发 AI 流式回复
- `🎵音乐`：获取随机热歌并播放
- `⛅天气 [城市]` 或 `⛅天气 城市`：查询指定城市天气
- `🎬电影 <链接>`：解析播放指定电影链接
- `📰新闻`：获取最新新闻条目并展示
- `📺b站视频 <链接>`：解析播放 B 站视频
- 支持 Emoji 输入与高亮显示

## 常见问题与排查
- `404 GET /@vite/client`：IDE 预览伪请求，非项目路由，忽略即可
- jQuery 加载失败（`net::ERR_ABORTED`）：确认本地文件存在；已实现 CDN 自动回退
- 端口占用（`WinError 10048`）：
  - 查占用：`netstat -ano | findstr :8891`
  - 结束进程：`taskkill /PID <PID> /F`
- AI 模型名问题：如需使用其它模型，设置 `SILICONFLOW_MODEL` 环境变量即可

## 验证步骤
- 打开 `http://127.0.0.1:8891/login` 进入登录页
- 在聊天页输入消息，查看群聊消息滚动与功能卡片展示
- 输入包含 `🤖成小理` 的消息，观察 AI 流式回复是否正常


