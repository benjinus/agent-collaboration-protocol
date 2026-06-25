# Agent Collaboration Protocol

Agent Collaboration Protocol（ACP）是一个面向 AI Agent 的、与厂商无关的文件协作协议。它适用于多个 Agent 无法直接互发消息，但可以读写同一个共享文件夹的场景。

ACP schema v2 是 deliverable-aware 的破坏性重构版本。每个 completed run 都必须包含一个声明好的 Markdown primary deliverable、deliverable 生命周期事件、SHA-256 冻结快照、readiness gates，以及最终的 `conclusion.md` receipt。旧的非 deliverable ACP 目录不再被本 schema 支持。

## 安装到 Agent

推荐安装：

```bash
npx skills add benjinus/agent-collaboration-protocol
```

手动安装：

```bash
git clone https://github.com/benjinus/agent-collaboration-protocol.git
```

把克隆得到的目录复制到目标 Agent 的 skill 或 instruction 目录，或者让 Agent 读取其中的 `SKILL.md`。

## 会创建什么

internal mode 的 ACP 目录结构：

```text
<collaboration-folder>/
├── protocol.json
├── events.jsonl
├── proposal.md
├── review.md
├── decisions.md
├── readiness.md
├── conclusion.md
└── deliverables/
    └── <primary>.md
```

协议文件留在协作目录根目录。真正可交付的文档放在 `deliverables/`。`conclusion.md` 是最终协议收据，不是 primary deliverable。

## 发起协作

```bash
python3 scripts/init_collaboration.py \
  --folder <collaboration-folder> \
  --participant <participant-a> \
  --participant <participant-b> \
  --objective "<一个明确的决策或交付物>" \
  --primary-deliverable-type design-spec \
  --completion "<objective gate>" \
  --completion "<another objective gate>"
```

内置 primary deliverable 类型：

- `adr`
- `design-spec`
- `implementation-plan`
- `decision-memo`
- `review-report`
- `test-plan`

只有在提供 `--primary-deliverable-file` 和至少一个 `--primary-deliverable-check` 时，才使用 `custom`。

external mode 示例：

```bash
python3 scripts/init_collaboration.py \
  --folder <repo>/.acp/<run> \
  --participant <participant-a> \
  --participant <participant-b> \
  --objective "<objective>" \
  --primary-deliverable-type adr \
  --deliverables-mode external \
  --repo-root ../.. \
  --deliverables-dir docs/architecture \
  --completion "<objective gate>"
```

external mode 会把产物写入 repo-root-relative 的 deliverables dir，并在 events、readiness、conclusion 中使用 `external:<file>` 引用。

## 事件流程

允许的事件：

- `initialized`
- `deliverable_drafted`
- `deliverable_revised`
- `deliverable_frozen`
- `proposal_submitted`
- `review_submitted`
- `proposal_revised`
- `question_classified`
- `decision_proposed`
- `decision_accepted`
- `readiness_passed`
- `completed`
- `blocked`

`initialized` 之后的所有事件都需要 `reply_to`。所有 `deliverable_*` 事件都需要 `doc` 和 `role`。`deliverable_frozen` 还需要顶层 `sha256` 字段。

阶段保持不变：

- `drafting`
- `reviewing`
- `revising`
- `decision_review`
- `readiness_check`
- `completed`
- `blocked`

## 参与方运行循环

没有原生 watcher 时：

```bash
python3 scripts/wait_for_turn.py \
  --folder <collaboration-folder> \
  --participant <participant-id>
```

然后查看下一步：

```bash
python3 scripts/next_action.py \
  --folder <collaboration-folder> \
  --participant <participant-id>
```

只执行当前 phase 允许的动作，追加对应事件，然后继续循环，直到 phase 变为 `completed` 或 `blocked`。

## Readiness Gate

写入 `readiness_passed` 或 `completed` 前，`readiness.md` 必须满足：

- 开放问题已 resolved、带 Reason deferred，或 blocking。
- 不存在 blocking 或 unresolved 问题。
- Objective gates 已勾选。
- Generated deliverable gates 已勾选。
- Primary deliverable 是 `Status: Frozen`。
- Primary deliverable SHA-256 snapshot 已记录。
- `Ready to implement` 已勾选。

只要 readiness 里仍有 unresolved 或 blocking 项，`decision_accepted` 就无效。

## 最终结论

`conclusion.md` 是最终 receipt。它必须包含 outcome（`[proceed]`、`[do_not_proceed]` 或 `[defer]`）、rationale、deliverable receipt、accepted decisions summary、readiness result、assumptions、deferred follow-ups、implementation blockers 和 next action。

`blocked` 是 phase/event，不是可 completed 的 outcome。

## 校验

```bash
python3 scripts/validate_collaboration.py --folder <collaboration-folder>
```

退出码：

- `0`：校验通过。
- `1`：校验通过但有 warning。
- `2`：校验失败。

## License

MIT. See `LICENSE`.
