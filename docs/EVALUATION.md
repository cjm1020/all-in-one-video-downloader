# AI Coding 评估方法与证据规则

本仓库有可复用的任务和软件验证记录，尚未提供不同模型在同一基线下的独立对照实验。代码测试通过证明相应实现满足已检查的条件，不自动等于「某模型具备专家能力」。真实验证结果统一记录在 [VERIFICATION](VERIFICATION.md)，任务输入与验收在 [TASK_CATALOG](TASK_CATALOG.md)。

## 一次可比较的评测

1. 记录仓库基线 commit、任务编号与版本。确认目标参考实现没有进入被测上下文；可从功能实现前的版本出题，或预先准备未公开的需求变体。
2. 固定允许使用的网络、工具、时间、依赖和测试资源。外部站点/模型调用作为单独集成阶段，不能因网络波动把所有失败归因于模型。
3. 向模型提供业务背景、输入契约、不可变约束和验收要求，不直接提供解法。保留完整提示和操作轨迹。
4. 收取补丁、变更说明、测试输出与已知限制。用独立验收用例检查正常路径、边界、故障和回归；不只运行模型自己写的测试。
5. 由评审者按同一评分表逐项评分，记录需要的人工纠正和原因。多人评审时报告分歧，不把不存在的评审团队写入结果。
6. 保存输出 commit 与证据，标明 `passed`、`failed`、`not_run`、`blocked_external`。未执行的项目不能写为通过。

正式比较至少应覆盖同一任务的多次独立运行，并报告样本数及分布。单次演示可展示能力，但无法提供稳定成功率。

## 统一 100 分量表

任务目录中的专项权重用于该任务内部；下表提供跨任务汇总维度。维度分为 0、1、2、3、4 级，按 `等级 / 4 × 权重` 计分。

| 维度 | 权重 | 0 级 | 2 级 | 4 级 |
| --- | --- | --- | --- | --- |
| 业务与契约正确性 | 30 | 未完成主要需求或输出不可用 | 正常路径可用，边界存在缺项 | 需求、边界、数据语义与失败反馈均符合契约 |
| 安全与数据一致性 | 25 | 可跨文件/对象边界或损坏资料 | 主要保护存在，异常/并发证据不足 | 授权门禁、事务、引用、输入边界有独立反例验证 |
| 验证质量 | 20 | 没有有效证据或伪造通过 | 正常测试通过，缺故障/回归 | 可复现命令、独立用例、故障及回归覆盖，与实测输出一致 |
| 架构与可维护性 | 15 | 耦合破坏已有边界或大量无关改动 | 可运行，职责/生命周期仍模糊 | 变更边界清楚、恢复路径明确、资源成本有依据 |
| 交付与诚实说明 | 10 | 虚构模型调用、测试或商业结果 | 有说明但遗漏限制 | 产物可审查，已验证与未验证分开，人工介入和不足透明 |

1 级和 3 级表示相邻描述之间的状态，必须附具体观察。不能单凭行数、提交数或模型自述打分。

## 严重失败规则

- 越过媒体目录、访问受禁止内网、绕过交付门禁、暴露密钥或破坏用户资料：记录严重失败，安全维度为 0，整体结果不得标记通过。
- 捏造测试、付费调用、用户反馈、Stars 或工作经历：诚实维度为 0，整次结果无效。
- 依靠新增空提交或拆分无业务价值文件满足记录数量：不视为任务完成证据。
- 独立验收出现未修复关键回归：即使总分较高，也只能记录未通过。

建议的完成阈值为总分至少 80，且业务、安全与验证均至少 3 级，没有严重失败。该阈值是评估设计，未被宣称为任何机构的官方标准。

## 证据分层

| 层级 | 能证明什么 | 不能证明什么 |
| --- | --- | --- |
| 模型与数据库测试 | 输入约束、事务、引用与确定性规则 | 浏览器操作、真实下载、生产负载 |
| API 集成测试 | HTTP 行为、错误码、状态与输出内容 | 真正来源可访问或浏览器没有交互问题 |
| 前端类型与构建 | 类型关系与生产包能构建 | UI 可操作、布局或所有交互正确 |
| 浏览器端到端 | 页面路径、持久刷新、真实播放器/下载交互 | 所有来源站点、长期稳定性 |
| 真实来源验证 | 在给定时间/网络/授权环境下的具体样例 | 所有平台、其他地区或会员素材 |
| 商业试点 | 受访者实际任务、时间与付费行为 | 无样本外推的收入预测或产品市场匹配 |

脚本和自动化用例应保存实际失败输出。手动观察注明观察者和方法；截图只能证明所截页面当时的状态。

## 运行记录模板

以下是待填写模板，没有默认成功值。保存为独立评测记录，并避免提交原始客户资料、Cookie 或 API 密钥。

```yaml
evaluation_id: "待填写"
task_id: "T01"
task_version: "1"
baseline_commit: "待填写完整 SHA"
output_commit: "待填写完整 SHA"
model_and_configuration: "待填写实际模型、推理与采样配置"
started_at: "待填写带时区的时间"
environment: "待填写系统、依赖、允许工具与网络"
prompt_artifact: "待填写脱敏提示文件路径"
status: "not_run"
human_interventions: []
checks: [] # 每项包括 command、exit_code、result、evidence_path
scores: null # 每个维度包含等级、加权分、观察依据
critical_failures: []
unverified: []
```

比较结果应同时展示任务成功率、分数、人工介入、时长与工具/模型成本。成本没有真实日志时标注缺失；没有实际 token 计量时不按文本长度估成精确账单。

## 当前可检查的材料

- [任务目录](TASK_CATALOG.md)：12 个真实工作流任务，包含输入、约束、失败模式、验收与权重。
- [架构说明](ARCHITECTURE.md)：单机边界、队列并发、数据演进及多用户迁移的决策条件。
- [验收记录](VERIFICATION.md)：当前软件实测与明确限制；不要把旧版本测试数沿用到本轮提交。
- `backend/tests` 与 `frontend/tests`：可运行的软件验收入口。模型独立评测需要额外按本文件建立运行记录。

可直接定位的验收用例包括：

| 能力/反例 | 测试文件与真实符号 | 证据范围 |
| --- | --- | --- |
| 项目客户、预算与时区日期 | `backend/tests/test_studio_projects.py::test_project_creation_persists_client_budget_and_deadline` | 隔离数据库中的 API 持久化 |
| 项目成员替换原子性 | `backend/tests/test_studio_membership.py::test_membership_replacement_is_atomic_and_deduplicated` | 无效成员整体回滚与去重 |
| 授权输入与证据 | `backend/tests/test_studio_rights.py::test_rights_reject_incomplete_or_unsafe_evidence` | 受约束的人工授权资料；不鉴定证据真伪 |
| 字幕时间与查询文字 | `backend/tests/test_knowledge.py::test_caption_search_returns_real_timestamps_and_literal_query` | 测试字幕和字面查询，不是语义搜索 |
| 自动卡片来源失效 | `backend/tests/test_knowledge.py::test_cards_require_source_deduplicate_and_invalidate_only_generated` | 自动卡片去重与失效，人工卡片保留 |
| 复习时间规则 | `backend/tests/test_knowledge.py::test_schedule_is_deterministic` | 固定时间下三档调度，不证明学习效果 |
| 剪辑时间轴与条件完成 | `backend/tests/test_knowledge.py::test_caption_clip_rebase_and_conditional_completion` | 字幕重定位和状态条件写入 |
| 恢复与旧进程租约 | `backend/tests/test_queue.py::test_stop_lease_blocks_resume_and_delete_until_worker_exits` | API 状态冲突；真实子进程续传另看集成记录 |
| 重定向出站边界 | `backend/tests/test_security.py::test_connection_guard_checks_redirect_hosts` | 受控解析反例，不攻击实际第三方 |

符号存在不等于本轮已经运行通过。实际命令、版本、结果与新增交付/浏览器检查统一以验收报告为准。

适合申报的证据是「有真实需求、能定义能力边界、实现能被复现、失败可以解释」。资格所需的工作经历或项目热度仍须由外部事实提供，见 [PORTFOLIO](PORTFOLIO.md)。
