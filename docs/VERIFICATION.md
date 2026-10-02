# 验收记录

## 1.1.0 商业工作流验收 · 2026-10-03

环境：Windows、Python 3.12.8 本地验证、Docker Linux Python 3.11 镜像、Node 24、Edge Chromium。以下是本轮实际运行结果，初版历史记录保留在后文。

| 验证 | 实际结果 |
| --- | --- |
| 后端回归 | **99 passed**，含 39 项原测试、44 项 Studio 业务测试和 16 项字幕知识 / 升级测试；约 11 秒 |
| 静态检查 | 后端 app/tests Ruff、三份新增验收脚本 Ruff、Git diff 空白检查通过 |
| 前端发布构建 | `vue-tsc -b && vite build` 通过；Docker 内使用 1.1.0 包版本完成生产构建 |
| 浏览器 | **8 passed**，最终约 23 秒：项目创建 / 授权 / 实际交付门禁、排队字幕学习 / 手写书签及卡片 / 到期复习、自定义配方去重及日志、经营估算和 390px 布局，加上四项原工作台回归 |
| 商业 API 验收 | `scripts/verify_commercial.py` **6 项通过**：未完成交付拒绝、unknown 授权拒绝核验、字幕时间证据、卡片去重 / 提前复习拒绝、配方重复执行、清单及真实操作数据 |
| 实际 CC0 交付 | `scripts/verify_delivery.py` 成功下载 MDN 官方 GitHub 原文件并剪成 1 秒；媒体 **96,426 bytes**，ZIP **99,453 bytes**；包内媒体与文件接口逐字节一致，SHA-256 与清单一致 |
| 部署 | 最新 web / api / worker 全部 healthy，仍使用原持久卷；原有两份媒体可播放，新增表初始化正常 |
| 旧片段升级 | 初版把完整源时长记在片段上；现有库初始化会修正片段时长，重复初始化仍保留素材和知识资料；回归已覆盖 |
| 提交历史 | 从原来 20 条提交继续增加，全部为实际文件变更；`scripts/audit_history.py --minimum 51 --base 8ae5d90` 可复核当前数量、增量和空提交 |

本轮独立审阅后修复：TXT / 字幕正文以 NOTE 开头和纯数字时被误删、多语言关键词搜索大小写规则不一致、缺失媒体仍能标记交付、排队字幕资料搜索后内容不可见，以及开发代理 Host 改写导致同源请求被拒绝。均有实际回归证据。

真实下载首次访问 `interactive-examples.mdn.mozilla.net` 遇到 SSL EOF 和握手超时。未关闭 TLS 或地址保护；改用同一 MDN 官方仓库的 CC0 原文件后，真实下载、播放与打包成功。浏览器测试支持 `TEST_MEDIA_URL`，交付脚本支持 `--media-url`，让网络条件可复现。

真实媒体 SHA-256：`47e1e83388e218ffc5c43c6b7702c57b7a2e9f07f47b31f070c94b45fce24f99`。验收创建的临时任务、项目及自定义配方均被清理；操作记录保留。该结果验证软件和文件交付，不证明真实付费客户、版权法律判断或模型任务评分。

最新截图：[创作交付](screenshots/studio.png)、[经营洞察](screenshots/insights.png)、[移动端交付](screenshots/mobile-studio.png)。截图中的项目明确标记为演示，预算为 0，无真实客户或收入；素材使用已有真实 CC0 下载。演示资料仅在本机持久卷，仓库不包含数据库，新部署从空库开始。

本轮未调用付费 DeepSeek、未评测其他模型，也未重复声称初版的平台解析结果全部在本轮复验。GitHub Actions 已补充商业 API、真实 ZIP 验收和失败截图上传；托管运行是否通过以 Actions 页面为准。第三方 AnyIO 弃用提示仍存在，不影响上述通过结果。

## 初版历史验收 · 2026-10-02

验证日期：2026-10-02（Asia/Shanghai）。运行环境：Windows + Docker Desktop Linux 容器，Python 3.11 后端镜像，Node 24 / Vue 3 前端，Edge Chromium 浏览器。

## 已通过

| 验证 | 结果与证据 |
| --- | --- |
| 项目顺序 | 第 1 条提交只包含 DESIGN / RESEARCH，后续实现，最终 20 条真实提交 |
| 后端回归 | `python -m pytest -q`：39 passed；URL 与 DNS 检查、映射 IPv6、连接重定向、只读 Cookie、事务领取、租约、暂停冲突、预约、去重、路径、Range、合集、导出、摘要、口令及同源限制 |
| 代码检查 | `python -m ruff check app tests` 通过；前端 `vue-tsc -b && vite build` 通过 |
| Docker | 实际构建与启动 web / api / worker，三容器 healthy，网页只绑定本机 8090；运行用户均非 root |
| 浏览器 | Playwright 4 项通过：预约与暂停 / 恢复 / 取消；创建合集与 Tab 焦点；390px 五个页面无水平溢出；真实视频加载、笔记持久化、星标、字幕导入、本地摘要、导出与封面 |
| 公开直链下载 | MDN CC0 Flower：真实解析、下载、剪辑、文件 Range、字幕导入、摘要与 Markdown；`scripts/smoke.py` 通过 |
| 精确剪辑 | FFprobe 验证视频 H.264 + AAC，片段 2.002 秒，190,525 字节 |
| 音频口袋 | FFprobe 验证 MP3，片段 2.040 秒，32,977 字节 |
| 本地封面 | 下载后 FFmpeg 生成 JPEG，认证后可通过 poster 接口访问 |
| 暂停与续传 | 48 KB/s 的真实下载在 17.79% 暂停，进度稳定；恢复后完成 3 秒片段，283,497 字节；`scripts/verify_resume.py` 通过 |
| 重启持久化 | 同时重启三个容器后，两份真实素材、合集、星标、标签、笔记、字幕与摘要仍可读取，Range 返回 206 |
| YouTube | 官方 Blender《Big Buck Bunny 60fps 4K》成功解析标题、635 秒时长及多清晰度；通勤预设分离音视频下载、合并、两秒剪辑与 Range 文件交付通过 |
| Bilibili | 指定课程中引用的 `BV1YvmbYbEgS` 成功解析中文标题、3401.676 秒及 360/480/720/1080p；未下载该教程视频 |
| GitHub | main 分支正常推送；没有强推、空提交或改写远程历史 |

最终镜像实测 Node `v24.21.0`，yt-dlp 已识别 `node` JavaScript runtime。API / Worker 为 UID 10001，Nginx 为 UID 101，均非 root。最终镜像上的 4 项 Playwright 全部通过（约 30 秒），YouTube 端到端也再次通过。

## 实测中修复的问题

- Docker Hub 连接失败：使用可配置的公开 ECR 镜像源，默认官方镜像仍可用。
- Debian HTTP 下载源 502 / 连接失败：使用 HTTPS、包缓存与重试。
- 浏览器 number 输入默认整数步长导致小数剪辑无法提交：添加 0.01 秒步长。
- 保存请求完成晚于关闭弹窗时重新打开资料卡：只更新仍选中的任务，防止异步回调重建弹窗。
- 立即恢复或删除尚未退出的下载进程：通过清理租约阻止竞争，Worker 结束后释放。
- 只读 Cookie 退出时被下载引擎重写：只加载，不回写会话文件，并添加回归测试。
- 旧演示链接失效：切换到已验证的 MDN CC0 素材。
- Debian 默认 Node 20 不被当前 yt-dlp JS 解析接受：后端单独引入 Node 24 与 yt-dlp-ejs。

## 截图及演示内容

[工作台](screenshots/home.png)、[队列](screenshots/queue.png)、[媒体收藏](screenshots/library.png)、[学习花园](screenshots/learning.png)、[设置](screenshots/settings.png)、[移动端](screenshots/mobile.png) 均为本机真实网页截图。截图显示的两份 CC0 素材来自实际下载，字幕明确标记为验证示例，不是花朵视频的原字幕。

本机保留这两条演示记录便于用户检查；数据库和媒体不上传 GitHub，新的部署从空库开始。截图脚本 `scripts/capture.mjs` 使用已经运行的服务，不注入虚假记录。

## 验证范围与限制

- DeepSeek 接口已实现，缺少用户密钥，未进行真实付费模型调用；本地提取与未配置时的错误反馈已验证。
- 未声称所有平台都验证或可用；抖音、会员内容、地区网络和来源 Cookie 需按具体授权环境测试。不实现 DRM 绕过。
- 自动下载来源已有的英文 / 中文字幕；没有字幕时可导入，不提供语音转写。导出整理后的 TXT 和完整 Markdown/JSON；首版没有时间轴对齐的 SRT/VTT 二次导出。
- 清晰度预设使用“优先”选择，来源没有对应格式时由 yt-dlp 选择可下载格式，实际媒体编码以来源为准。
- 片段需要先下载整个原视频，因此长视频剪辑仍耗费原视频下载流量。
- 续传依赖源站支持和签名地址有效期；媒体浏览器兼容性依赖来源编码。
- 单机 SQLite、一个 Worker、可信单用户架构；默认本机开放，公开部署需口令及 HTTPS。
- pytest 存在第三方 AnyIO / Starlette 的弃用提示，不影响 39 项通过结果。
- CI 工作流已提交，包含后端检查、前端构建和完整 Docker / 浏览器测试。GitHub 托管运行结果以仓库 Actions 页面为准。
