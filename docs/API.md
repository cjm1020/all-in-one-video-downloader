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

## 创作交付

新增接口沿用同源会话权限，适用于可信单用户工作空间。项目中的客户字段是业务记录，不创建客户登录账号。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET/POST | /api/studio/projects | 项目列表 / 创建项目 |
| GET/PATCH/DELETE | /api/studio/projects/{id} | 项目详情 / 更新资料与状态 / 移除项目，保留媒体 |
| PUT | /api/studio/projects/{id}/items | 整体替换素材关联，最多 500 项，全部存在才提交 |
| GET/PUT | /api/studio/rights/{task_id} | 查询 / 保存素材授权记录 |
| GET | /api/studio/projects/{id}/export | 交接资料，`format=markdown` / `json` / `csv` |
| GET | /api/studio/projects/{id}/package | 包含实际媒体及授权清单的 ZIP，重新核验交付条件 |
| GET/POST | /api/studio/workflows | 内置及自定义配方 / 保存配方 |
| DELETE | /api/studio/workflows/{id} | 删除自定义配方，内置配方不可删除 |
| POST | /api/studio/workflows/{id}/run | 按配方批量创建任务，可关联项目 |
| GET | /api/studio/analytics | 实际项目、媒体、来源和最近操作记录 |

项目创建与更新支持 `name`、`client`、`budget_cents`、`due_at`、`notes`；更新还支持 `status`（`draft` / `active` / `delivered`）。预算使用整数分，属于用户输入，不代表收入。截止日期包含时区；PATCH 中传 `due_at: null` 清除截止日期，其他字段不接受 null。

详情返回 `project`、`items`、`checklist`。每份素材具有 `rights` 对象，检查结果包含 `total`、`completed`、`licensed`、`ready` 和 `issues`。非空项目的所有素材下载完成且授权核验有效时，才允许标记交付。已交付项目需重新打开后修改素材关联；素材被删除、状态降级或授权撤回时，项目会自动回到进行中并留下记录。

授权输入：

```json
{
  "license": "cc-by",
  "attribution": "作者 · 作品名 · 来源 · CC BY 4.0 · 修改说明",
  "evidence_url": "https://example.com/license",
  "verified": true
}
```

授权类型支持 `unknown`、`owned`、`cc0`、`cc-by`、`permission`。CC BY 必须填写署名，单独授权必须填写证据链接，unknown 不允许 verified=true。系统保存负责人核验结果，不自动判定版权归属；证据链接只做 URL 格式与地址校验，不抓取页面。返回值包含 task_id 和 updated_at，更新请求只传上述四个输入字段。

配方支持 `name`、`description`、`preset`、`collection_id`、`tags`、`rate_limit`。运行请求为 `{"urls":["https://example.com/owned.mp4"],"project_id":null}`，最多 30 个链接，全部通过公网 URL 校验后事务入库。响应为 `added` 和 `skipped`；重复项保持原任务的资料和关联。合集被删除后，自定义配方回退到 inbox。向已交付项目运行配方返回 409。

## 字幕证据与复习

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | /api/knowledge/search?q=关键词&limit=20 | 跨素材原句检索，关键词最大 100 字符，limit 为 1–100 |
| GET/POST | /api/knowledge/tasks/{task_id}/markers | 查询 / 创建时间标记 |
| DELETE | /api/knowledge/markers/{id} | 删除时间标记 |
| GET/POST | /api/knowledge/tasks/{task_id}/cards | 查询 / 手写复习卡 |
| POST | /api/knowledge/tasks/{task_id}/cards/generate | 本地提取最多 8 张字幕原句填空卡 |
| GET | /api/knowledge/cards/due?limit=50 | 到期复习卡，limit 为 1–200 |
| POST | /api/knowledge/cards/{id}/review | 记录评级，更新下次复习日期 |
| DELETE | /api/knowledge/cards/{id} | 删除复习卡 |
| GET | /api/knowledge/tasks/{task_id}/brief | 内容制作简报，`format=markdown` / `json` |

搜索响应为 `{"results":[{"task_id":"…","title":"…","text":"原句片段","start":1,"end":4}],"total":1}`。SRT/VTT 保留有效时间戳；TXT 和旧库只有文本时返回 start/end=null，不推测时间。通配符作为普通字符。下载剪辑时保留与剪辑重叠的字幕，并将时间戳平移到片段起点。

时间标记输入 `{"position":1.5,"label":"关键观点","notes":"编辑备注","color":"sage"}`。位置不能超过已知媒体时长；标题最大 120 字符，备注最大 5000 字符，颜色支持 sage / peach / lavender / sky。每个素材最多 200 个标记。

复习卡输入 `{"question":"问题","answer":"参考答案"}`；每个素材最多 200 张，相同问答不重复创建。生成卡的 answer 包含原句，响应 mode=local-extraction。字幕替换会清除旧摘要、更新检索索引并删除源哈希失效的自动卡，保留手写卡。重复生成跳过已有卡。

复习请求 `{"rating":"good"}`，支持 again / good / easy。首次分别安排 10 分钟 / 1 天 / 4 天；后续 good 将天数乘 2，easy 乘 3，上限 365 天，again 重置进度。未到期重复提交返回 409，写事务防止双击累计复习次数。这是简单的本地日程规则，不宣称采用完整 SM-2 算法。

简报导出汇总保存的字幕原句、编辑笔记、标签和时间标记，明确标注本地提取及人工复核要求。没有字幕时仍可导出并说明来源缺失；不生成无来源事实。
