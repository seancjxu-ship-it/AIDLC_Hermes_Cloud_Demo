---
name: aidlc-orchestration
description: Plan and coordinate the governed AIDLC multi-agent workflow.
---

# AIDLC Orchestration / AIDLC 编排

Create an ordered Dev → QA → Review → Deploy task graph. Every task must declare inputs, allowed tools, acceptance criteria, token evidence, and a deterministic gate. Stop on a denied mandatory gate. Never bypass human approval for merging to main.

创建有序的 Dev → QA → Review → Deploy 任务图。每个任务必须声明输入、允许工具、验收条件、Token 证据和确定性门禁。强制门禁失败时停止，禁止绕过合并到 main 的人工审批。

