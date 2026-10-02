# API

通过网页服务访问同源 `/api`。请求与响应使用 JSON，文件和 SSE 除外。设置口令后，先 `POST /api/session` 传入 `{"token":"口令"}`，后续携带会话 Cookie。未配置口令时可在本机直接使用。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /api/health | 数据库及 API 存活，无需口令 |
| GET/POST/DELETE | /api/session | 会话状态 / 登录 / 退出 |
| GET | /api/status | Worker、引擎、FFmpeg、AI、存储 |
| GET/PUT | /api/settings | 默认预设、KB/s 限速、GB 限额 |
| POST | /api/inspect | 单视频解析，50 秒超时 |
| GET/POST | /api/tasks | 列表 / 批量创建（最多 30 条） |
| GET/PATCH/DELETE | /api/tasks/{id} | 详情 / 修改资料卡 / 删除及清理 |
| POST | /api/tasks/{id}/actions/{action} | pause / resume / cancel / retry |
| GET | /api/tasks/{id}/file | 播放，支持 Range；`?download=true` 保存 |
| GET | /api/tasks/{id}/poster | 下载后生成的本地 JPEG 封面，要求认证 |
| GET | /api/tasks/{id}/export | 默认 Markdown；`?format=json` 或 `transcript` |
| GET/POST | /api/collections | 合集列表 / 创建 |
| DELETE | /api/collections/{id} | 删除，内容移回 inbox |
| POST | /api/tasks/{id}/transcript | 导入字幕，清除旧摘要 |
| POST | /api/tasks/{id}/summary | local 原句提取 / ai DeepSeek |
| GET | /api/events | `event: tasks` SSE，数据为任务列表，1.5 秒轮询数据库 |

创建任务：

```json
{
  "urls": ["https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"],
  "preset": "everyday",
  "collection_id": "inbox",
  "scheduled_at": null,
  "clip_start": null,
  "clip_end": null,
  "rate_limit": 0
}
```

预设：everyday / archive / commute / audio。返回 `{"added":[...],"skipped":[重复链接]}`，同 URL + 预设 + 剪辑范围为去重键，失败或取消的旧任务不阻止重新添加。批量链接全部通过安全校验后才入库，避免半成功提交。

预约时间需包含时区，存储为 UTC；剪辑起止同时填写、结束晚于开始。修改资料卡支持 title / collection_id / favorite / tags / notes，不接受任意状态或文件路径。

任务列表不包含大段字幕、摘要和笔记，改用 `has_transcript` / `has_summary`；详情接口返回完整内容。内部文件路径和租约不向客户端暴露。

错误：400 无效链接 / 输入；401 需口令；403 跨源请求；404 任务或文件缺失；409 状态冲突或未准备好；422 模型或站点解析错误；429 解析并发繁忙；502 AI/解析服务错误；503 AI 未配置；504 解析超时。API 错误在 `detail` 字段中。
