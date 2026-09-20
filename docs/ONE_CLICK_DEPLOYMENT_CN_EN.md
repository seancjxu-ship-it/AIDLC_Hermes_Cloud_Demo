# One-click deployment and destruction / 一键部署与销毁

The package can create an independent AIDLC Demo after the operator supplies a Huawei Cloud account, a Hong Kong MaaS API key, and a GitHub token. It does not reuse hard-coded resource IDs from the current online environment.

该交付包可在操作者提供华为云账号、香港 MaaS API Key 和 GitHub Token 后创建一套独立的 AIDLC Demo，不复用当前在线环境的固定资源 ID。

## What is automated / 自动化范围

- Terraform: VPC, subnet, security group, CCE control plane, one CCE worker/ECS, two EIPs, DCS Redis, SWR organization and two private repositories. / Terraform：VPC、子网、安全组、CCE 控制面、一个 CCE Worker/ECS、两个 EIP、DCS Redis、SWR 组织和两个私有仓库。
- Docker: build and push the AIDLC platform image to SWR. / Docker：构建 AIDLC 平台镜像并推送到 SWR。
- Kubernetes and Helm: namespace, temporary SWR pull credential, application secrets, API, Orchestrator, Dev, QA, Review and Deploy Pods. / Kubernetes 与 Helm：Namespace、临时 SWR 拉取凭证、应用 Secret、API、Orchestrator、Dev、QA、Review 与 Deploy Pod。
- Verification: rollout checks and the public `/health` endpoint. / 验证：Deployment Rollout 与公网 `/health` 健康检查。
- Destruction: preview workloads, namespace, SWR image tags, and all Terraform-managed resources. / 销毁：Preview 工作负载、Namespace、SWR 镜像标签和全部 Terraform 管理资源。

## Prerequisites / 前置条件

- Windows PowerShell 5.1 or PowerShell 7. / Windows PowerShell 5.1 或 PowerShell 7。
- Huawei Cloud KooCLI (`hcloud`) in `PATH`. / `PATH` 中可用的华为云 KooCLI（`hcloud`）。
- Docker Desktop running. / Docker Desktop 已启动。
- Internet access to Huawei Cloud, GitHub, HashiCorp, Kubernetes and Helm download sites. / 可访问华为云、GitHub、HashiCorp、Kubernetes 与 Helm 下载站点。
- IAM permissions to create/delete VPC, EIP, CCE, ECS/EVS, DCS and SWR resources. / 具备创建和删除 VPC、EIP、CCE、ECS/EVS、DCS 与 SWR 的 IAM 权限。

Terraform, kubectl and Helm are downloaded into the ignored `.tools` directory when absent. Docker Desktop and KooCLI are intentionally treated as workstation prerequisites.

如果本机缺少 Terraform、kubectl 或 Helm，脚本会下载到已忽略的 `.tools` 目录。Docker Desktop 与 KooCLI 作为工作站前置条件处理。

## Credentials / 凭证

The script reads credentials from environment variables or asks interactively. It never writes them into the repository.

脚本优先从环境变量读取凭证，未设置时交互式询问；不会把凭证写入代码仓。

```powershell
$env:HUAWEICLOUD_ACCESS_KEY = "<AK>"
$env:HUAWEICLOUD_SECRET_KEY = "<SK>"
$env:AIDLC_MAAS_API_KEY     = "<Hong-Kong-MaaS-Key>"
$env:AIDLC_GITHUB_TOKEN     = "<GitHub-Fine-Grained-PAT>"
```

The GitHub token needs repository **Contents: Read and write** and **Pull requests: Read and write** for the customer application repository. / GitHub Token 需要对客户业务代码仓具备 **Contents: Read and write** 与 **Pull requests: Read and write** 权限。

## Deploy / 部署

```powershell
Set-Location <repository-root>
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\deploy.ps1"
```

Optional customer-restricted access example / 可选：仅允许客户出口 IP：

```powershell
.\scripts\cloud\deploy.ps1 -AllowedConsoleCidr "203.0.113.10/32"
```

Default output / 默认输出：

- Region: `sa-brazil-1`; MaaS endpoint: Hong Kong `ap-southeast-1`. / 区域：`sa-brazil-1`；MaaS：香港 `ap-southeast-1`。
- Console: `http://<node-eip>:30080`. / Console：`http://<节点EIP>:30080`。
- Login: `demo / huawei123`. / 登录：`demo / huawei123`。

## Status / 状态

```powershell
.\scripts\cloud\status.ps1
```

## Destroy / 销毁

```powershell
.\scripts\cloud\destroy.ps1
```

The script requires typing `DESTROY`. Automation systems may use `-Force`. Destruction is refused when `.aidlc-deployment.json` is absent, which reduces the chance of targeting an unrelated stack.

脚本要求输入 `DESTROY`；自动化系统可使用 `-Force`。如果缺少 `.aidlc-deployment.json`，脚本会拒绝销毁，以降低误操作到其他环境的风险。

## Demo boundary / Demo 边界

This package intentionally uses a single CCE worker and a single-node Redis instance, without multi-AZ, backup or disaster recovery. It is a customer demonstration package, not a production landing zone.

该交付包刻意采用单个 CCE Worker 与单节点 Redis，不包含多可用区、备份或容灾，是客户演示包而不是生产 Landing Zone。

