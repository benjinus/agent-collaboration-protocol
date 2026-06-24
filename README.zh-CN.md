# Agent Collaboration Protocol

Agent Collaboration Protocol 是一个面向 AI Agent 的、与厂商无关的文件协作协议。它适用于多个 Agent 无法直接互发消息，但可以读写同一个文件夹的场景。

协议通过一个小型状态机、结构化事件、readiness gate 和 validator 检查来约束协作过程。Agent 不能只因为双方“口头接受”就结束协作；必须先分类开放问题、清除阻塞项、通过 readiness，写出最终结论，再完成协作。

协议是按轮次交接的。发起方提交方案后必须等待，只有被列入等待列表的评审方可以推进评审阶段。发起方可以轮询或在真实超时/阻塞时标记 blocked，但不能在评审未完成时继续编辑共享文档。

## 安装到 Agent

推荐安装方式：

```bash
npx skills add benjinus/agent-collaboration-protocol
```

`skills` CLI 会检测支持的 Agent，并把 skill 安装到用户选择的 Agent 位置。

当 CLI 不可用时，可以手动安装：

```bash
git clone https://github.com/benjinus/agent-collaboration-protocol.git
```

把克隆得到的目录复制到目标 Agent 的 skill 或 instruction 目录，或者直接让 Agent 读取克隆目录中的 `SKILL.md`。

## 会创建什么

一个 ACP 协作目录包含：

- `protocol.json`：协作目标、参与方、完成门槛和当前阶段。
- `events.jsonl`：只追加的结构化事件日志，`seq` 必须连续。
- `proposal.md`：当前方案。
- `review.md`：结构化评审意见。每条 review 的标题必须使用对应 `review_submitted` 事件的 seq。
- `decisions.md`：只记录已经接受的决策。
- `readiness.md`：开放问题分类、阻塞项、延后但不阻塞的事项，以及最终实施准备状态。
- `conclusion.md`：对协作目标的最终回答：做、不做、还是延后；原因是什么；如何做或为何不做；下一步是什么。

协议不使用额外状态文件。协作状态只能有一个事实来源。

## 发起协作

可以把下面这段提示发给任何安装了本协议，或可以读取本仓库的 Agent：

```text
使用 Agent Collaboration Protocol 发起一个基于文件的协作。

协作目录：
<绝对路径或仓库相对路径>

参与方：
- <参与方-a>
- <参与方-b>

当前参与方：
<参与方-a>

目标：
<一个明确的决策或交付物>

完成门槛：
- <证明已接受决策是明确的门槛>
- <证明 readiness 已通过且没有阻塞项的门槛>
- <证明每个参与方都已完成的门槛>
```

## 事件流程

允许的事件：

- `initialized`
- `proposal_submitted`
- `review_submitted`
- `proposal_revised`
- `question_classified`
- `decision_proposed`
- `decision_accepted`
- `readiness_passed`
- `completed`
- `blocked`

阶段：

- `drafting`：正在准备方案。
- `reviewing`：等待另一方评审。
- `revising`：方案负责人处理评审意见。
- `decision_review`：先分类开放问题，再由参与方接受明确决策。
- `readiness_check`：分类开放问题并清除阻塞项。
- `completed`：协作完成。
- `blocked`：协作被阻塞。

## Readiness Gate

写入 `readiness_passed` 或 `completed` 前，`readiness.md` 必须满足：

- 每个开放问题都标记为 `[resolved]`、`[deferred_nonblocking]` 或 `[blocking]`。
- 每个 `[deferred_nonblocking]` 都包含 `Reason: ...`。
- 不存在 `[blocking]` 或 `[unresolved]`。
- `Ready to implement` 检查项已经勾选。

同样的问题分类也必须发生在参与方接受决策之前。只要仍有 unresolved 或 blocking 问题，接受决策就是无效的。

## 最终结论

Readiness 通过后，协作必须产出 `conclusion.md`。它是用户可以据此行动的结论文档：这个功能做不做，或者是否延后；原因、已接受决策、实施方式、假设、后续事项、阻塞项和下一步都必须写清楚。

## License

MIT. See `LICENSE`.
