# Terraform infrastructure / Terraform 基础设施

This module creates the minimum Huawei Cloud resources required by the demo in `sa-brazil-1`: VPC, subnet, security group, two EIPs, one CCE cluster, one CCE worker/ECS, one DCS Redis instance, and two private SWR repositories.

该模块在 `sa-brazil-1` 创建 Demo 所需的最小华为云资源：VPC、子网、安全组、两个 EIP、一个 CCE 集群、一个 CCE Worker/ECS、一个 DCS Redis 实例和两个私有 SWR 仓库。

MaaS remains in Hong Kong and is consumed through its OpenAI-compatible endpoint. The MaaS API key is not managed by Terraform and is injected into Kubernetes at deploy time.

MaaS 继续使用香港资源池，并通过 OpenAI 兼容接口调用。MaaS API Key 不由 Terraform 管理，而是在部署应用时注入 Kubernetes。

Use the repository-level scripts:

使用代码仓根目录下的脚本：

```powershell
.\scripts\cloud\deploy.ps1
.\scripts\cloud\status.ps1
.\scripts\cloud\destroy.ps1
```

Terraform state contains generated node and Redis passwords. It is excluded by `.gitignore`; protect the workstation that runs the deployment.

Terraform State 包含自动生成的节点和 Redis 密码，已通过 `.gitignore` 排除；请保护执行部署的工作站。

