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
- Internet access to Huawei Cloud, GitHub, HashiCorp, Kubernetes and Helm download sites. / 可访问华为云、GitHub、HashiCorp、Kubernetes 与 Helm 下载站点。
- IAM permissions to create/delete VPC, EIP, CCE, ECS/EVS, DCS and SWR resources. / 具备创建和删除 VPC、EIP、CCE、ECS/EVS、DCS 与 SWR 的 IAM 权限。

The scripts download missing Terraform, kubectl, Helm and KooCLI into the ignored `.tools` directory. If Docker Desktop is absent, they download the official installer, install it for the current user, start it and wait for the Docker Engine.

脚本会把缺少的 Terraform、kubectl、Helm 和 KooCLI 下载到已忽略的 `.tools` 目录。如果没有 Docker Desktop，则下载官方安装程序、为当前用户安装、启动并等待 Docker Engine。

Docker Desktop's first launch may still require accepting its license, enabling WSL 2, approving elevation or restarting Windows. / Docker Desktop 首次启动时仍可能要求接受许可、启用 WSL 2、确认管理员授权或重启 Windows。

## Beginner workstation setup / 新手工作站准备

Use a short local path without line breaks, for example `C:\aidlc\AIDLC_Hermes_Cloud_Demo`. Do not copy a path that the display has wrapped into two lines. / 建议把仓库放在没有换行的短路径下，例如 `C:\aidlc\AIDLC_Hermes_Cloud_Demo`。不要把界面自动折行后的路径复制成两行。

### 1. Open and verify PowerShell / 打开并检查 PowerShell

Windows 10 and Windows 11 normally include Windows PowerShell 5.1. Open **Start**, search for **Windows PowerShell**, and run: / Windows 10 和 Windows 11 通常自带 Windows PowerShell 5.1。打开**开始菜单**，搜索 **Windows PowerShell**，然后执行：

```powershell
$PSVersionTable.PSVersion
```

`Major` must be `5` or higher. PowerShell 7 is optional. Install it with WinGet if desired, then open **PowerShell 7** or run `pwsh`. / `Major` 必须为 `5` 或更高。PowerShell 7 是可选项；如需安装，可执行以下 WinGet 命令，然后打开 **PowerShell 7** 或运行 `pwsh`。

```powershell
winget install --id Microsoft.PowerShell --source winget
```

Official guide / 官方说明：[Install PowerShell on Windows](https://learn.microsoft.com/powershell/scripting/install/install-powershell-on-windows)

If Windows blocks local scripts, use `-ExecutionPolicy Bypass` as shown below. It affects only that PowerShell process and does not require a machine-wide policy change. / 如果 Windows 阻止本地脚本，请按下文使用 `-ExecutionPolicy Bypass`；它只对该 PowerShell 进程生效，无需修改整机策略。

### 2. Automatic KooCLI setup and manual fallback / KooCLI 自动准备与手工备用方案

Normally no manual installation is required: the scripts download the official Windows archive and copy `hcloud.exe` into `.tools`. Use the steps below only when automatic download is blocked. / 正常情况下无需手工安装：脚本会下载官方 Windows 压缩包，并把 `hcloud.exe` 放入 `.tools`。只有自动下载被阻止时，才使用下面的手工备用步骤。

1. Download **KooCLI for Windows** from the Huawei Cloud official page. / 从华为云官方页面下载 **Windows 版 KooCLI**。
2. Decompress it and place `hcloud.exe` in a stable directory, for example `C:\Tools\HuaweiCloud\KooCLI`. / 解压后，把 `hcloud.exe` 放到固定目录，例如 `C:\Tools\HuaweiCloud\KooCLI`。
3. Open **Start > Edit environment variables for your account > Path > Edit > New**, add that directory, and save. / 打开**开始菜单 > 编辑账户的环境变量 > Path > 编辑 > 新建**，加入该目录并保存。
4. Close all PowerShell windows, open a new one, and verify: / 关闭所有 PowerShell 窗口，重新打开一个窗口并验证：

```powershell
Get-Command hcloud
hcloud version
```

Official guide / 官方说明：[Installing KooCLI in Windows](https://support.huaweicloud.com/intl/en-us/qs-hcli/hcli_02_003_01.html)

For a temporary test in the current window, prepend the directory without changing the permanent PATH: / 如果只想在当前窗口临时测试，可以不修改永久 PATH：

```powershell
$env:Path = "C:\Tools\HuaweiCloud\KooCLI;$env:Path"
hcloud version
```

The deployment script passes AK/SK to each KooCLI request. Running `hcloud configure init` is therefore **not required**, which also avoids storing permanent AK/SK in a KooCLI profile. / 部署脚本会在每次 KooCLI 请求中传入 AK/SK，因此**不需要**执行 `hcloud configure init`，也可避免把长期 AK/SK 保存到 KooCLI 配置文件。

### 3. Automatic Docker setup and first-launch actions / Docker 自动安装与首次启动操作

When Docker is missing, the scripts download the official x86-64 installer, perform a per-user installation, start Docker Desktop and wait up to 180 seconds for the engine. / 如果缺少 Docker，脚本会下载官方 x86-64 安装程序、执行当前用户安装、启动 Docker Desktop，并等待 Docker Engine 最长 180 秒。

If the script reports that the engine is not ready, complete these one-time manual actions: / 如果脚本提示 Engine 尚未就绪，请完成以下一次性人工操作：

1. Open Docker Desktop and accept its license when prompted. The WSL 2 backend is suitable for most Windows 10/11 workstations. / 打开 Docker Desktop，并按提示接受许可；对大多数 Windows 10/11 工作站，选择 WSL 2 后端即可。
2. If WSL is missing, open PowerShell **as Administrator**, run `wsl --install`, restart Windows if requested, and then start Docker Desktop. / 如果没有 WSL，请以**管理员身份**打开 PowerShell，执行 `wsl --install`，按提示重启 Windows，然后启动 Docker Desktop。
3. Wait until Docker Desktop reports that the engine is running. / 等待 Docker Desktop 显示 Engine 已运行。
4. Verify that both Docker Client and Server are displayed: / 验证输出中同时存在 Docker Client 与 Server：

```powershell
wsl --version
docker version
```

Official guide / 官方说明：[Install Docker Desktop on Windows](https://docs.docker.com/desktop/setup/install/windows-install/)

Docker Desktop licensing is governed by Docker's current subscription terms. Enterprise customers should confirm usage with their software-asset administrator. / Docker Desktop 的使用受 Docker 当前订阅条款约束，企业客户应由软件资产管理员确认许可要求。

### 4. Check outbound network access / 检查公网访问

The workstation or corporate proxy must allow outbound TCP 443. Docker pulls `python:3.11-slim`, and Terraform downloads the Huawei Cloud provider. The practical allowlist is: / 工作站或企业代理必须允许 TCP 443 出站访问。Docker 会拉取 `python:3.11-slim`，Terraform 也会下载华为云 Provider。建议放行：

- `github.com`, `api.github.com` / GitHub code and API / GitHub 代码与 API
- `releases.hashicorp.com`, `registry.terraform.io` / Terraform and provider / Terraform 与 Provider
- `dl.k8s.io` / kubectl
- `get.helm.sh` / Helm
- `auth.docker.io`, `registry-1.docker.io` and the Docker image CDN / Docker Hub 与镜像 CDN
- `*.huaweicloud.com`, `*.myhuaweicloud.com` / Huawei Cloud APIs and SWR / 华为云 API 与 SWR
- `api-ap-southeast-1.modelarts-maas.com` / Hong Kong MaaS GLM-5.2 / 香港 MaaS GLM-5.2

Use this quick TCP test. `TcpTestSucceeded` should be `True`; this checks reachability, not application authentication. / 可使用下面的命令快速检查 TCP；`TcpTestSucceeded` 应为 `True`。该结果只代表端口可达，不代表业务鉴权成功。

```powershell
@(
  "github.com",
  "releases.hashicorp.com",
  "registry.terraform.io",
  "dl.k8s.io",
  "get.helm.sh",
  "registry-1.docker.io",
  "swr.sa-brazil-1.myhuaweicloud.com",
  "api-ap-southeast-1.modelarts-maas.com"
) | ForEach-Object {
  Test-NetConnection $_ -Port 443 |
    Select-Object ComputerName, RemotePort, TcpTestSucceeded
}
```

If a corporate proxy performs TLS inspection or requires authentication, ask the network administrator to configure Windows, PowerShell and Docker Desktop consistently. / 如果企业代理进行 TLS 检查或要求认证，请让网络管理员统一配置 Windows、PowerShell 与 Docker Desktop 的代理。

### 5. Grant Huawei Cloud IAM permissions / 配置华为云 IAM 权限

For the first demo, the simplest path is to let a Huawei Cloud account administrator deploy it. For a dedicated IAM user, ask the cloud administrator to create a user group and authorize it in the **Brazil `sa-brazil-1` project**. / 第一次演示最简单的方式是由华为云账号管理员执行部署。如果使用独立 IAM 用户，请让云管理员创建用户组，并在**巴西 `sa-brazil-1` 项目**内授权。

| System policy or role / 系统策略或角色 | Why it is needed / 用途 |
|---|---|
| `VPC FullAccess` | VPC, subnet, security group and EIP / VPC、子网、安全组、EIP |
| `ECS FullAccess` | CCE worker ECS lifecycle / CCE 工作节点 ECS 生命周期 |
| `EVS FullAccess` | CCE worker system disk / CCE 工作节点系统盘 |
| `CCE Administrator` | Cluster lifecycle and Kubernetes resources / 集群生命周期与 Kubernetes 资源 |
| `DCS FullAccess` | Redis instance lifecycle / Redis 实例生命周期 |
| `SWR Admin` | Repositories, temporary credentials and image tags / 仓库、临时凭证与镜像标签 |

Console procedure / 控制台操作：

1. Sign in as the account administrator and open **IAM > User Groups > Create User Group**. / 使用账号管理员登录，打开 **IAM > 用户组 > 创建用户组**。
2. Open the new group, choose **Authorize**, select the permissions above, and set the scope to the Brazil project containing `sa-brazil-1`. / 打开新用户组，选择**授权**，勾选上述权限，授权范围选择包含 `sa-brazil-1` 的巴西项目。
3. Add the deployment IAM user to this group. / 把用于部署的 IAM 用户加入该用户组。
4. On first use, open the CCE console as an administrator and accept the prompt to create the CCE system agency if it appears. / 首次使用时，以管理员身份打开 CCE 控制台；如果出现创建 CCE 系统委托的提示，请确认授权。
5. Confirm sufficient CCE, ECS/EVS, EIP and DCS quotas and permission to create pay-per-use resources. / 确认 CCE、ECS/EVS、EIP 和 DCS 配额足够，并且账号能够创建按需资源。

For strict least-privilege environments, the customer's cloud administrator should derive a custom policy from the Terraform resources and CCE agency actions instead of retaining broad system roles. / 对最小权限要求严格的环境，应由客户云管理员根据 Terraform 资源与 CCE 委托操作制定自定义策略，而不是长期保留较宽泛的系统角色。

Official references / 官方参考：[Huawei Cloud system-defined permissions](https://support.huaweicloud.com/intl/en-us/permissions/iam_01_0001.html), [CCE permissions](https://support.huaweicloud.com/intl/en-us/usermanual-cce/cce_10_0187.html), [CCE system agencies](https://support.huaweicloud.com/intl/en-us/usermanual-cce/cce_10_0556.html)

### 6. One-command or two-command deployment / 一条命令或两条命令部署

Recommended one-command mode: `deploy.ps1` automatically runs preflight, prepares all tools, checks Docker, asks for the user's application repository URL and credentials, creates Huawei Cloud resources and deploys the Demo. / 推荐的一条命令模式：`deploy.ps1` 会自动执行预检查、准备全部工具、检查 Docker、询问用户自己的业务仓地址与凭证、创建华为云资源并部署 Demo。

```powershell
Set-Location "C:\aidlc\AIDLC_Hermes_Cloud_Demo"
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\deploy.ps1"
```

Two-command mode is useful when the operator wants to validate the workstation before creating billable cloud resources: / 如果操作者希望在创建计费云资源前先验证工作站，可使用两条命令模式：

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\preflight.ps1"
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\deploy.ps1" -SkipToolBootstrap
```

The scripts create `.tools`, download missing Terraform/kubectl/Helm/KooCLI, add that directory to `PATH` only for the script process, and install/start Docker Desktop when needed. They do not add `.tools` to the machine-wide `PATH`. / 脚本会创建 `.tools`，下载缺少的 Terraform/kubectl/Helm/KooCLI，只在当前脚本进程中加入 `PATH`，并按需安装和启动 Docker Desktop；不会把 `.tools` 加入整机 `PATH`。

Expected final message / 预期最终提示：

```text
Preflight passed / 部署前检查通过。
```

`.tools` is excluded by `.gitignore` and must not be committed. If automatic download is blocked, place `terraform.exe`, `kubectl.exe`, `helm.exe` and `hcloud.exe` directly in `.tools`. / `.tools` 已被 `.gitignore` 排除，不应提交到 Git。如果自动下载被阻止，可把 `terraform.exe`、`kubectl.exe`、`helm.exe` 和 `hcloud.exe` 直接放入 `.tools`。

For a centrally managed corporate workstation, IT can install Docker first and the operator can disable automatic Docker installation: / 如果企业工作站由 IT 统一管理软件，可先由 IT 安装 Docker，并禁用自动安装：

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\preflight.ps1" -SkipDockerDesktopInstall
```

### 7. Final beginner checklist / 新手最终检查清单

Run these commands in a **new PowerShell window** from the repository root: / 在仓库根目录下打开一个**新的 PowerShell 窗口**并执行：

```powershell
$PSVersionTable.PSVersion
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\preflight.ps1"
```

The workstation is ready when PowerShell is 5.1 or later and preflight prints `Preflight passed`. The script verifies all four CLI tools and both Docker Client and Server. / 当 PowerShell 为 5.1 或更高版本，并且预检查输出 `Preflight passed` 时，工作站准备完成；脚本会验证四个 CLI 工具以及 Docker Client 与 Server。

| Symptom / 现象 | Action / 处理方法 |
|---|---|
| Preflight cannot find `hcloud` / 预检查找不到 `hcloud` | Check the KooCLI download URL or place `hcloud.exe` in `.tools`. / 检查 KooCLI 下载地址，或把 `hcloud.exe` 放入 `.tools`。 |
| Docker shows Client but no Server / Docker 只有 Client、没有 Server | Start Docker Desktop and wait for the engine. / 启动 Docker Desktop 并等待 Engine 就绪。 |
| Download has proxy/certificate errors / 下载出现代理或证书错误 | Ask the network administrator to allow the listed domains and configure the corporate proxy/CA. / 让网络管理员放行域名并配置企业代理或 CA。 |
| Huawei Cloud returns `403` or `AccessDenied` / 华为云返回 `403` 或 `AccessDenied` | Check authorization in the Brazil project and all listed services. / 检查权限是否授予到巴西项目且覆盖上述全部服务。 |
| Script execution is disabled / 禁止执行脚本 | Use `powershell -ExecutionPolicy Bypass -File ...`. / 使用 `powershell -ExecutionPolicy Bypass -File ...`。 |
| A copied `-File` path contains a line break / `-File` 路径中出现换行 | Move the repository to a short path and enter the command on one physical line. / 把仓库移到短路径，并确保命令在同一物理行内。 |

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

The token belongs to the person deploying the Demo and must be authorized for the repository passed through `-RepositoryUrl`. A new user should fork the sample application repository and use their own fine-grained token for that fork. Never reuse the original owner's token. / Token 应属于当前部署 Demo 的用户，并对 `-RepositoryUrl` 指定的业务仓库有权限。新用户应 Fork 示例业务仓，并使用自己针对该 Fork 创建的 Fine-grained Token，绝不能复用原仓所有者的 Token。

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
