---
name: aidlc-swr-delivery
description: Build a real application image with Kaniko, push it to Huawei Cloud SWR, deploy a digest-pinned CCE Preview workload, and record verifiable delivery evidence.
---

# SWR and CCE Delivery / SWR 与 CCE 交付

## Stage / 所属环节

Deploy Worker — Build, publish, preview deployment, and smoke-test gate.

Deploy Worker——镜像构建、发布、预览部署和冒烟测试门禁。

## Required inputs / 必需输入

- Git repository URL, feature branch, and exact commit SHA. / Git 仓库地址、功能分支和精确 Commit SHA。
- Repository Dockerfile. For this demo only, Dev Worker may add a minimal scaffold when absent. / 仓库内 Dockerfile；仅在本 Demo 中，缺失时可由 Dev Worker 加入最小脚手架。
- SWR repository and Kubernetes docker-config Secret. / SWR 镜像仓与 Kubernetes Docker 配置 Secret。
- Target CCE namespace, application port, and smoke-test contract. / 目标 CCE Namespace、应用端口和冒烟测试契约。

## Procedure / 执行步骤

1. Create a run-specific Kaniko Job in CCE. / 在 CCE 中创建本次任务专属的 Kaniko Job。
2. Check out the exact feature commit, never a moving branch head. / 拉取精确的功能分支提交，不使用可能变化的分支头。
3. Build and push `<swr-repository>:<commit-prefix>`. Never publish only `latest`. / 构建并推送 `<swr-repository>:<commit-prefix>`，禁止只发布 `latest`。
4. Read and validate the real SHA-256 image digest. / 读取并校验真实 SHA-256 镜像摘要。
5. Create or update a run-specific CCE Deployment and Service using `image@sha256:...`. / 使用 `image@sha256:...` 创建或更新本次任务专属的 CCE Deployment 和 Service。
6. Wait for rollout, then execute health, functional, and idempotency smoke tests against the live Pod. / 等待发布完成，然后针对真实 Pod 执行健康、功能和幂等冒烟测试。
7. Record the Kaniko Job, SWR repository/tag/digest, CCE Deployment/Service/Pod/imageID, and every smoke-test result in the Evidence Pack. / 将 Kaniko Job、SWR 仓库/标签/摘要、CCE Deployment/Service/Pod/imageID 和全部冒烟测试结果写入 Evidence Pack。

## Gate rules / 门禁规则

- A build, push, rollout, digest, or smoke-test failure blocks the final decision. / 构建、推送、发布、摘要或冒烟测试任一失败，都会阻断最终决策。
- Deployment success does not imply permission to merge the Pull Request. / 部署成功不代表允许合并 Pull Request。
- Credentials must come from Kubernetes Secrets and must never appear in logs, evidence, Git, or model prompts. / 凭证必须来自 Kubernetes Secret，且不得出现在日志、证据、Git 或模型提示词中。
- Preview resources must be traceable to `run_id` and commit SHA. / Preview 资源必须能够追溯到 `run_id` 和 Commit SHA。

## Outputs / 输出

- Immutable image reference and digest. / 不可变镜像引用与摘要。
- CCE workload identity and rollout state. / CCE 工作负载标识与发布状态。
- Live Preview endpoint through the authenticated console proxy. / 通过 Console 鉴权代理访问的 Live Preview 地址。
- Structured, timestamped delivery evidence. / 结构化、带时间戳的交付证据。

