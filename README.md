# AIDLC Hermes Cloud Demo / AIDLC Hermes 云端 Demo

An executable AIDLC software-factory framework on Huawei Cloud. It connects a customer Git repository to a Hermes-style Orchestrator, role-specific Agent Workers, OpenSpec/AIDLC skills, ModelArts Studio MaaS GLM-5.2, DCS Redis, SWR and CCE.

这是一套运行在华为云上的可执行 AIDLC 软件工厂框架。它把客户 Git 代码仓与 Hermes 风格 Orchestrator、角色化 Agent Worker、OpenSpec/AIDLC Skills、ModelArts Studio MaaS GLM-5.2、DCS Redis、SWR 和 CCE 连接起来。

The objective is not to sell a complete coding product. The demo shows how a customer can open the full engineering lifecycle, reuse AIDLC practices, and consume Huawei Cloud MaaS throughout development and review.

目标不是出售一整套 Coding 产品，而是展示客户如何打开完整研发流程、复用 AIDLC 方法，并在开发与评审过程中持续使用华为云 MaaS。

## What is real / 哪些环节是真实执行

1. Read the requirement and OpenSpec artifacts from Git. / 从 Git 读取需求与 OpenSpec 产物。
2. Build a stage-gated task graph in the Orchestrator. / Orchestrator 生成带门禁的任务图。
3. Dev Agent calls GLM-5.2, changes source, checks, commits and pushes a feature branch. / Dev Agent 调用 GLM-5.2、修改代码、检查、提交并推送功能分支。
4. QA and Review Agents run deterministic tests, compile checks, secret scans and model-assisted review. / QA 与 Review Agent 执行确定性测试、编译检查、密钥扫描和模型辅助评审。
5. Deploy Agent creates a Kaniko Job, pushes the image to SWR, resolves the real digest, deploys a run-specific CCE Preview and executes smoke tests. / Deploy Agent 创建 Kaniko Job、推送镜像到 SWR、读取真实摘要、部署任务专属 CCE Preview，并执行冒烟测试。
6. The system creates a Pull Request and seals a timestamped Evidence Pack. Merge remains a human decision. / 系统创建 Pull Request 并封装带时间戳的 Evidence Pack；最终合并仍由人工决定。

## Runtime architecture / 运行架构

- `aidlc-api`: REST API, Basic Auth, dashboard, events/evidence views and authenticated Preview reverse proxy. / REST API、Basic Auth、Dashboard、事件/证据展示与 Preview 鉴权反向代理。
- `hermes-orchestrator`: skills loading, task DAG, state transitions, routing and final decision. / Skills 加载、任务 DAG、状态迁移、路由和最终决策。
- `hermes-sf-dev`: GLM-assisted change, local checks, Git commit and push. / GLM 辅助修改、本地检查、Git Commit 与 Push。
- `hermes-sf-qa`: deterministic repository tests and acceptance evidence. / 确定性代码仓测试与验收证据。
- `hermes-sf-review`: compile, secret scan, changed-file review and policy gate. / 编译、密钥扫描、变更评审与策略门禁。
- `hermes-sf-deploy`: Kaniko, SWR, digest-pinned CCE Preview, smoke tests and Pull Request. / Kaniko、SWR、按摘要固定的 CCE Preview、冒烟测试与 Pull Request。
- `DCS Redis`: run state, queues, events, evidence and history. / 任务状态、队列、事件、证据和历史统计。

Brazil `sa-brazil-1` hosts the execution and data plane. Hong Kong `ap-southeast-1` hosts MaaS GLM-5.2. / 巴西 `sa-brazil-1` 承载执行面和数据面；香港 `ap-southeast-1` 承载 MaaS GLM-5.2。

## Customer input contract / 客户输入契约

The customer prepares: / 客户需要准备：

- Git repository URL and base branch. / Git 仓库地址与基线分支。
- Fine-grained GitHub token with **Contents: Read and write** and **Pull requests: Read and write**. / 具备 **Contents: Read and write** 与 **Pull requests: Read and write** 权限的 Fine-grained GitHub Token。
- Requirement file, for example `demo/GITHUB_ISSUE.md`. / 需求文件，例如 `demo/GITHUB_ISSUE.md`。
- `sdd/spec.md`, `sdd/design.md`, `sdd/tasks.yaml` and repository-owned tests. / `sdd/spec.md`、`sdd/design.md`、`sdd/tasks.yaml` 与代码仓自带测试。
- Optional customer skills under `.hermes/skills/`. / 可选的客户自定义 Skills，放在 `.hermes/skills/`。
- Human merge and release approval policy. / 人工合并与发布审批策略。

The current demo does not accept a free-form inline requirement. The requirement must live in Git so the input is versioned and auditable. / 当前 Demo 不接收自由文本需求；需求必须进入 Git，才能被版本化和审计。

## API / 接口

- `GET /health` — platform health / 平台健康检查
- `GET /api/architecture` — deployed architecture / 已部署架构
- `GET /api/dashboard` — history, success rate, token usage, duration and event counts / 历史任务、成功率、Token、耗时与事件统计
- `POST /api/runs` — start a full AIDLC run / 启动完整 AIDLC 任务
- `GET /api/runs/{run_id}` — state and final decision / 状态与最终决策
- `GET /api/runs/{run_id}/events` — timestamped internal events / 带时间戳的内部事件
- `GET /api/runs/{run_id}/evidence` — structured Evidence Pack / 结构化证据包
- `GET /preview/{run_id}/{path}` — authenticated proxy to the run-specific Preview / 鉴权访问本次任务专属 Preview

Example / 示例：

```json
{
  "repository": "https://github.com/seancjxu-ship-it/AIDLC_Simple_Order_Demo",
  "base_branch": "main",
  "requirement_file": "demo/GITHUB_ISSUE.md",
  "execution_mode": "live",
  "skill_profile": "openspec-core+aidlc-demo",
  "model": "glm-5.2"
}
```

## One-click deploy and destroy / 一键部署与销毁

The reusable package creates its own VPC, subnet, security group, CCE cluster, CCE worker/ECS, EIPs, DCS Redis and private SWR repositories. It then builds the platform image, pushes it to SWR and installs the six Pods with Helm.

可复用交付包会创建独立的 VPC、子网、安全组、CCE 集群、CCE Worker/ECS、EIP、DCS Redis 与私有 SWR 仓库，然后构建平台镜像、推送到 SWR，并通过 Helm 安装六类 Pod。

Prerequisites: Windows PowerShell, KooCLI `hcloud`, and a running Docker Desktop. Terraform, kubectl and Helm are bootstrapped into the ignored `.tools` directory when absent. / 前置条件：Windows PowerShell、KooCLI `hcloud` 和已启动的 Docker Desktop。如果缺少 Terraform、kubectl 或 Helm，脚本会安装到已忽略的 `.tools` 目录。

Credentials are read from environment variables or requested interactively; they are never committed. / 凭证从环境变量读取或交互式输入，绝不提交到代码仓。

```powershell
$env:HUAWEICLOUD_ACCESS_KEY = "<AK>"
$env:HUAWEICLOUD_SECRET_KEY = "<SK>"
$env:AIDLC_MAAS_API_KEY     = "<Hong-Kong-MaaS-Key>"
$env:AIDLC_GITHUB_TOKEN     = "<GitHub-Fine-Grained-PAT>"

.\scripts\cloud\deploy.ps1
.\scripts\cloud\status.ps1
.\scripts\cloud\destroy.ps1
```

Default login / 默认登录：`demo / huawei123`.

The destroy script requires the local deployment record and explicit `DESTROY` confirmation. It cleans Preview workloads, the namespace, SWR image tags and all resources managed by the same Terraform state. / 销毁脚本要求存在本地部署记录并显式输入 `DESTROY`，会清理 Preview 工作负载、Namespace、SWR 镜像标签，以及同一 Terraform State 管理的全部资源。

Full instructions / 完整说明：[docs/ONE_CLICK_DEPLOYMENT_CN_EN.md](docs/ONE_CLICK_DEPLOYMENT_CN_EN.md)

## Documentation / 文档

- [Detailed design / 详细设计](docs/AIDLC_DETAILED_DESIGN_CN_EN.md)
- [Skills catalog and stage mapping / Skills 清单与阶段映射](docs/SKILLS_CATALOG_CN_EN.md)
- [One-click deployment / 一键部署](docs/ONE_CLICK_DEPLOYMENT_CN_EN.md)
- [Customer PowerPoint / 客户 PPT](docs/presentation/AIDLC_Hermes_Detailed_Design_CN_EN.pptx)

## Local development / 本地开发

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements-dev.txt
.\.venv\Scripts\python -m unittest discover -s tests -v
```

```powershell
docker compose up --build
```

## Demo boundary / Demo 边界

This repository intentionally targets a low-cost customer demo: one CCE worker and single-node Redis, without multi-AZ, backup, disaster recovery or production-grade identity integration. / 本仓库刻意面向低成本客户演示：单个 CCE Worker、单节点 Redis，不包含多可用区、备份、容灾或生产级身份集成。

