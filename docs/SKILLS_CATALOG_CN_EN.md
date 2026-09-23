# AI-DLC Skills Catalog and Stage Mapping / AI-DLC Skills 清单与环节映射

> Language / 语言: **English / 中文** | [Português (Brasil)](CATALOGO_DE_SKILLS_PT_BR.md)

This document explains every Skill packaged in the demo, where it is used, what it consumes, and what evidence it produces.

本文说明 Demo 中预置的全部 Skill、所在研发环节、输入内容、执行动作及输出证据。

## How Skills are used / Skills 如何被使用

Hermes Orchestrator selects Skills according to the task graph and passes only the relevant Skill context to each Worker. OpenSpec Skills govern requirement and change artifacts; AIDLC Skills govern execution, quality gates, cloud delivery, and evidence.

Hermes Orchestrator 按任务图选择 Skills，并只把当前任务需要的 Skill 上下文传给对应 Worker。OpenSpec Skills 管理需求与变更产物；AIDLC Skills 管理执行、质量门禁、云上交付和证据。

```text
Requirement / 需求
  -> Explore & Propose / 探索与提案
  -> Spec, Design, Tasks / 规格、设计、任务
  -> Development / 开发
  -> QA / 测试
  -> Review & Security / 评审与安全
  -> Kaniko Build -> SWR -> CCE Preview / 构建、镜像仓、预览环境
  -> PR + Evidence + Human Approval / PR、证据与人工审批
```

## Complete catalog / 完整清单

| Skill | Source / 来源 | Stage and executor / 环节与执行者 | Main input / 主要输入 | Output or gate / 输出或门禁 |
|---|---|---|---|---|
| `openspec-explore` | OpenSpec | Discovery; Hermes / 需求探索；Hermes | Business idea, problem, constraints / 业务想法、问题、约束 | Clarified scope and decisions; no code change / 明确范围与决策，不修改代码 |
| `openspec-propose` | OpenSpec | Requirement and planning; Hermes / 需求与规划；Hermes | Confirmed requirement / 已确认需求 | Proposal, spec, design, and tasks / 提案、规格、设计和任务 |
| `openspec-update-change` | OpenSpec | Change planning; Hermes / 变更规划；Hermes | Existing OpenSpec change plus new decisions / 既有变更及新决策 | Coherent updated planning artifacts; no code / 一致的规划产物，不修改代码 |
| `openspec-apply-change` | OpenSpec | Development; Dev Worker / 开发；Dev Worker | Approved spec, design, tasks, repository / 已批准规格、设计、任务和代码仓 | Implemented task changes / 已实现的任务变更 |
| `openspec-sync-specs` | OpenSpec | Specification governance; Hermes / 规格治理；Hermes | Accepted delta specs / 已接受的增量规格 | Main specifications synchronized / 主规格同步完成 |
| `openspec-archive-change` | OpenSpec | Closure; Hermes / 收尾；Hermes | Completed, approved change / 已完成并批准的变更 | Archived OpenSpec change / 已归档的 OpenSpec 变更 |
| `aidlc-orchestration` | Demo platform / Demo 平台 | End-to-end orchestration; Hermes / 端到端编排；Hermes | Run request and Skill registry / 任务请求与 Skill 注册表 | Dev → QA → Review → Deploy task graph, gates, final decision / 任务图、门禁和最终决策 |
| `aidlc-python-development` | Demo platform / Demo 平台 | Development; Dev Worker / 开发；Dev Worker | Repository, task, tests, GLM-5.2 context / 代码仓、任务、测试、GLM-5.2 上下文 | Source changes, passing local tests, feature commit and branch / 源码修改、本地测试、功能提交与分支 |
| `aidlc-test-execution` | Demo platform / Demo 平台 | Verification; QA Worker / 验证；QA Worker | Exact feature commit and repository tests / 精确功能提交与仓库测试 | Deterministic test results and PASS/FAIL gate / 确定性测试结果与通过/失败门禁 |
| `aidlc-code-review` | Demo platform / Demo 平台 | Code review; Review Worker / 代码评审；Review Worker | Spec, design, diff, compile results / 规格、设计、差异、编译结果 | Review findings and approval gate / 评审发现与批准门禁 |
| `aidlc-security-review` | Demo platform / Demo 平台 | Security review; Review Worker / 安全评审；Review Worker | Changed files and source content / 变更文件与源码内容 | Secret scan, secure-code findings, PASS/FAIL gate / 秘钥扫描、安全发现和门禁 |
| `aidlc-swr-delivery` | Demo platform / Demo 平台 | Delivery; Deploy Worker / 交付；Deploy Worker | Repository, feature branch, exact commit, Dockerfile, SWR Secret / 仓库、功能分支、精确提交、Dockerfile、SWR Secret | Kaniko Job, SWR tag and digest, CCE Preview, smoke tests / Kaniko Job、SWR 标签与摘要、CCE Preview、冒烟测试 |
| `aidlc-evidence-collector` | Demo platform / Demo 平台 | Evidence and audit; Hermes / 证据与审计；Hermes | Events and Worker outputs from the whole run / 全流程事件与 Worker 输出 | Timestamped Evidence Pack and traceable final decision / 带时间戳的证据包与可追溯最终决策 |

## Runtime mapping / 运行时映射

| Runtime step / 运行步骤 | Pod or component / Pod 或组件 | Skills loaded / 加载的 Skills | Visible evidence / 可见证据 |
|---|---|---|---|
| Accept request and build graph / 接收请求并生成任务图 | `aidlc-api`, `hermes-orchestrator` | `aidlc-orchestration`, relevant OpenSpec Skills / 编排 Skill 与相关 OpenSpec Skills | Run ID, requirement context, dispatch events / 任务 ID、需求上下文、分派事件 |
| Modify and commit source / 修改并提交源码 | `hermes-sf-dev` | `openspec-apply-change`, `aidlc-python-development` | Initial failed tests, corrected tests, changed files, branch, commit / 初始失败测试、修复后测试、文件、分支、提交 |
| Deterministic QA gate / 确定性 QA 门禁 | `hermes-sf-qa` | `aidlc-test-execution` | Test command, exit code, PASS/FAIL / 测试命令、退出码、通过/失败 |
| Review and security gates / 评审与安全门禁 | `hermes-sf-review` | `aidlc-code-review`, `aidlc-security-review` | Compile result, secret hits, model review / 编译结果、秘钥命中、模型评审 |
| Build, push, and preview / 构建、推送与预览 | `hermes-sf-deploy` plus run-specific Kaniko and Preview Pods / Deploy Worker 及任务专属 Kaniko、Preview Pod | `aidlc-swr-delivery` | Job, image tag, digest, Deployment, Service, Pod, imageID, smoke tests / Job、镜像标签、摘要、工作负载、Pod、imageID、冒烟测试 |
| PR and final evidence / PR 与最终证据 | `hermes-orchestrator` | `aidlc-evidence-collector` | Pull Request URL, final decision, Evidence Pack / PR 地址、最终决策、证据包 |

## Demo delivery Skill in detail / Demo 交付 Skill 详解

The delivery stage is real, not a manifest-only simulation:

交付阶段为真实执行，不再只是生成模拟清单：

1. Kaniko checks out the exact feature commit. / Kaniko 拉取精确的功能提交。
2. Kaniko builds and pushes `swr.sa-brazil-1.myhuaweicloud.com/aidlc-demo/order-demo:<commit-prefix>`. / Kaniko 构建并推送带 Commit 前缀标签的镜像。
3. The platform extracts the registry SHA-256 digest. / 平台提取镜像仓真实 SHA-256 摘要。
4. CCE deploys `image@sha256:<digest>`, so the Preview is immutable and traceable. / CCE 按镜像摘要部署，使 Preview 不可变且可追溯。
5. The Deploy Worker verifies health, order cancellation, and idempotency replay. / Deploy Worker 验证健康状态、取消订单和幂等重放。
6. Hermes records all results before it allows PR and Preview. / Hermes 记录全部结果后，才允许生成 PR 与 Preview。

## Customizing for a customer / 面向客户扩展

A customer can add a new Skill under `.hermes/skills/<skill-name>/SKILL.md` and register it in the stage-to-Skill mapping. A production integration should define the Skill's trigger, required inputs, allowed tools, deterministic gate, output schema, and evidence fields.

客户可在 `.hermes/skills/<skill-name>/SKILL.md` 中新增 Skill，并注册到阶段与 Skill 的映射中。生产集成应明确 Skill 的触发条件、必需输入、允许工具、确定性门禁、输出结构和证据字段。

Skills are execution instructions, not security credentials. GitHub tokens, Huawei Cloud AK/SK, MaaS keys, and SWR credentials must remain in Kubernetes Secrets and must never be written into Skill files or prompts.

Skills 是执行指令，不是安全凭证。GitHub Token、华为云 AK/SK、MaaS Key 和 SWR 凭证必须保存在 Kubernetes Secret 中，绝不能写入 Skill 文件或提示词。

