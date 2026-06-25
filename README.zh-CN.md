# Agent Collaboration Protocol

![License](https://img.shields.io/github/license/agi-connect/agent-collaboration-protocol)
![Skill](https://img.shields.io/badge/skill-agent--collaboration--protocol-blue)
![Deliverables](https://img.shields.io/badge/deliverables-Markdown-1f6feb)
![AI Collaboration](https://img.shields.io/badge/AI-collaboration-7c3aed)

[English](README.md)

Agent Collaboration Protocol（ACP）用于帮助 AI 智能体在共享工作空间中协作，即使它们不能依赖同一个连续对话线程。

ACP 适用于需要多个智能体一起做出明确决策、互相审阅工作、解决开放问题，并留下可继续使用的交付物的场景。

## 协作场景

ACP 支持一种结构化的智能体交流过程：

- 一个智能体发起协作，明确目标、参与方和预期交付物。
- 负责人起草方案和主要交付物。
- 其他参与方从各自角色出发审阅方案和交付物。
- 负责人根据反馈修订内容，记录已接受的决策，并处理开放问题。
- 参与方确认结果是否已经可以被后续使用。
- 协作以稳定的交付物和简短的最终收据结束。

这个过程适合架构决策、实现计划、设计评审、测试计划、编码智能体之间的交接，以及任何需要比自由聊天更严格协作纪律的工作流。

ACP 让协作围绕可观察的产物展开，而不是依赖隐藏的对话记忆。每个参与方都可以理解当前提出了什么、审阅了什么、接受了哪些决策，以及还有什么阻塞。

## 交付物

每个完成的 ACP 协作都会产出一个主要 Markdown 交付物。支持的交付物类型包括：

- 架构决策记录
- 设计规范
- 实现计划
- 决策备忘录
- 评审报告
- 测试计划
- 自定义 Markdown 交付物

最终收据和主要交付物是分开的。它用于总结结果、已接受的决策、就绪状态、前提假设、阻塞项和下一步行动。

## 安装到智能体

推荐使用 `npx skills add` 安装：

```bash
npx skills add agi-connect/agent-collaboration-protocol
```

这会把本技能安装到兼容智能体使用的本地技能目录中。

如果你的智能体不支持 `skills add`，也可以手动克隆仓库：

```bash
git clone https://github.com/agi-connect/agent-collaboration-protocol.git
```

然后让智能体读取仓库中的 `SKILL.md`，或者把仓库复制到该智能体会读取的技能目录或指令目录中。

## 使用这个技能

ACP 最适合在每个智能体都有明确协作角色时使用。通常由一个智能体作为发起者，其他智能体作为参与者加入同一个协作。

作为发起者，可以要求智能体启动一次 ACP 协作，并提供：

- 共享协作位置。
- 协作目标。
- 参与方名称或角色。
- 预期的主要交付物类型。
- 与目标相关的完成条件。

`<deliverable-type>` 可以使用以下交付物类型：

- `adr`：架构决策记录。
- `design-spec`：设计规范。
- `implementation-plan`：实现计划。
- `decision-memo`：简洁的决策备忘录。
- `review-report`：结构化评审报告。
- `test-plan`：测试计划。
- `custom`：参与方约定的其他 Markdown 交付物。

`<completion-criteria>` 用来描述判断协作目标已经完成的客观条件。好的完成条件应该可以被观察和审阅，例如：“设计取舍已经记录清楚”、“实现阶段已经可以执行”，或者“所有安全评审顾虑都有已接受的处理结论”。

发起者请求示例：

```text
使用 agent-collaboration-protocol 技能，在 <shared-folder> 中发起一次协作。
我是发起者。参与方是 <participant-a> 和 <participant-b>。协作目标是 <objective>。
主要交付物应为 <deliverable-type>。当 <completion-criteria> 时，协作即可完成。
```

作为参与者，可以要求智能体加入已有 ACP 协作，并提供：

- 同一个共享协作位置。
- 当前智能体要使用的参与方身份。
- 当前角色需要承担的审阅责任。

`<role-or-responsibility>` 用来描述该参与方在审阅中负责的视角或责任。可以使用具体职责，例如“实现可行性”、“安全评审”、“接口设计”、“测试覆盖”、“产品需求”或“文档清晰度”。

参与者请求示例：

```text
使用 agent-collaboration-protocol 技能，加入 <shared-folder> 中的协作。
我的参与方身份是 <participant-a>。请从 <role-or-responsibility> 的角度审阅当前方案和交付物。
```

发起者负责推动协作收敛到最终交付物。参与者负责读取当前状态、审阅方案和交付物、提出顾虑、接受决策，或者在工作尚未准备好时指出阻塞项。

## 许可证

MIT。见 `LICENSE`。
