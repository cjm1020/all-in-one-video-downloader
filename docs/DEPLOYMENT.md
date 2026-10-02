# Docker 部署与使用

## 服务

| 容器 | 职责 | 对外端口 |
| --- | --- | --- |
| web | Nginx 静态页面、同源 API/SSE 代理 | 默认本机 8090 |
| api | FastAPI、SQLite、媒体范围请求、字幕摘要 | 不公开 |
| worker | 串行领取队列，独立子进程下载与 FFmpeg 转码 | 不公开 |

API 和 Worker 共用命名卷 `all-in-one-video-downloader_library`。数据库为 `/data/library.sqlite3`，媒体为 `/data/media/{task_uuid}/`。web 只读运行；全部服务使用非 root 用户、去除 Linux capabilities、日志轮转和健康检查。Worker 下载进程组随暂停 / 取消终止，保留 `.part` 尝试续传。

## 配置

```bash
cp .env.example .env
docker compose up --build -d
docker compose ps
```

Windows PowerShell 用 `Copy-Item .env.example .env`。Compose 会自动创建本地空 `cookies` 目录，Git 忽略该目录。

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| HOST_BIND | 127.0.0.1 | 绑定地址 |
| WEB_PORT | 8090 | 网页端口 |
| ACCESS_TOKEN | 空 | 可选工作空间口令；公开访问必须设置随机长口令 |
| MAX_STORAGE_GB | 10 | 首次初始化存储限额；之后在页面偏好设置调整 |
| DEEPSEEK_API_KEY | 空 | 可选 AI 摘要密钥；只传给 API |
| DEEPSEEK_MODEL | deepseek-chat | 模型名称 |
| COOKIE_FILE | 空 | 授权会话的 Netscape Cookie 文件容器路径，如 `/cookies/authorized.txt` |
| PYTHON_IMAGE | python:3.11-slim | 后端基础镜像 |
| NODE_IMAGE | node:24-alpine | 前端构建基础镜像 |
| NODE_RUNTIME_IMAGE | node:24-bookworm-slim | 下载引擎的 Node 24 运行时 |
| NGINX_IMAGE | nginx:1.28-alpine | 网页运行镜像 |
| DEBIAN_MIRROR | https://deb.debian.org | Debian 包源基址，可替换为可信镜像 |

`.env`、Cookie 和本地下载文件均被 Git 忽略。设置 Cookie 后，应放入 `cookies/authorized.txt`；只读挂载保护原始会话文件。不能通过页面输入任意下载器命令、FFmpeg 命令或 Cookie 文本。

### Docker Hub 网络受限

可将以下内容加入本地 `.env`，使用公开 ECR 镜像：

```dotenv
PYTHON_IMAGE=public.ecr.aws/docker/library/python:3.11-slim
NODE_IMAGE=public.ecr.aws/docker/library/node:24-alpine
NODE_RUNTIME_IMAGE=public.ecr.aws/docker/library/node:24-bookworm-slim
NGINX_IMAGE=public.ecr.aws/docker/library/nginx:1.28-alpine
```

然后正常运行 `docker compose up --build -d`。项目 Dockerfile 缓存 Debian 包并对临时下载失败重试，首次安装 FFmpeg 可能需要数分钟。

后端镜像还包含 Node 24 和 yt-dlp-ejs，供 yt-dlp 的 JavaScript 解析使用；Debian 默认的 Node 20 不满足当前引擎要求，因此从单独的官方镜像复制运行时。依赖版本固定在 `backend/requirements.txt` 与 `frontend/package-lock.json`。

## 验证

打开工作台，点击“试试公开演示素材”，预览信息后“开始收藏”。使用 MDN 的 [CC0 Flower](https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4)。

下载队列可观察实时进度；完成后进入媒体收藏播放。音频口袋保存 MP3；在“更多小偏好”填写剪辑开始 / 结束秒数可生成独立片段。预约时间按浏览器本地时区转 UTC 存储。原始内容必须先完整下载，再进行精确剪辑。

在学习花园选择视频，导入 SRT/VTT/TXT，点击“提取本地要点”。配置 DeepSeek 后可生成 AI 摘要；未配置时按钮禁用且显示可用的本地模式。

```bash
python scripts/smoke.py
```

该脚本向本机服务添加一个短视频，验证解析、下载、文件 Range、字幕和资料卡，默认结束后删除它创建的任务；设 `KEEP_SMOKE_MEDIA=1` 可保留。如配置了口令，设置 `SMOKE_TOKEN`，避免将口令放进命令行参数。

进一步验证脚本：`scripts/verify_resume.py` 检查限速和下载中的暂停恢复；`scripts/verify_platform.py` 下载官方 Blender CC BY 短片以验证分离音视频合并；`scripts/verify_live.py` 生成两条真实 CC0 演示素材并重启当前项目的三个容器，核对媒体与笔记持久化。后两个操作包含实际下载，运行前确保当前没有需要保留运行状态的任务。

## 更新与备份

```bash
git pull
docker compose up --build -d
```

`docker compose down` 保留媒体卷；不要使用 `down -v`，它会删除持久化收藏。

先 `docker compose stop api worker`，再导出整个卷；备份包含 SQLite、可能存在的 WAL/SHM 文件和所有媒体，不只复制主数据库。

```bash
docker run --rm -v all-in-one-video-downloader_library:/data:ro \
  -v "$(pwd)/backups:/backup" python:3.11-slim \
  python -c "import shutil; shutil.make_archive('/backup/library', 'gztar', '/data')"
docker compose start api worker
```

Windows 将 `$(pwd)/backups` 换为明确的绝对路径。恢复时先停止 API / Worker，把完整备份解压回同一卷并恢复 UID 10001 的读写权限，再启动服务。不要同时运行两个 Compose 项目并共享该卷。

## 公开访问

在 `.env` 设置长随机 `ACCESS_TOKEN`，由自己的 HTTPS 反向代理转发到本机 8090；Nginx/代理需关闭 SSE 缓存，读取超时至少 180 秒。访问口令换成 HttpOnly、SameSite=Strict 会话 Cookie，文件与实时事件也要求认证。部署在反向代理后，请保证 Host 不被改写；如代理终结 TLS，可让内部 HTTP 仅在受控本机网络使用。

这是可信单用户工具，首版无用户隔离、注册 / 支付和多租户资源配额。

## 常见问题

- **网页等不到 Worker**：`docker compose ps` 与 `docker compose logs --tail=100 worker`。API 首次健康后 Worker 才启动；重启后活跃租约最长约 30 秒恢复。
- **站点下载失败**：检查错误详情、地区网络、yt-dlp 版本和该内容的授权会话。无 Cookie 下载并非所有平台都支持。
- **存储限额**：包括 `.part` 和中间文件。达到限额后停止下载；删除不用的任务会清理目录，不自动清除收藏。
- **播放失败**：来源编码可能不兼容浏览器。先保存文件用本地播放器查看；MP3/常见 MP4 最适合网页播放。
- **字幕缺失**：并非所有视频提供字幕。当前自动选择英文 / 中文字幕，可手动导入；不从无字幕视频猜测摘要。
- **无法续传**：续传依赖来源服务器、签名地址和 yt-dlp；暂停恢复时可能重新下载部分内容。
- **升级下载引擎**：更新并锁定 `backend/requirements.txt` 中 yt-dlp 版本，重新构建并运行回归与公开素材测试。
