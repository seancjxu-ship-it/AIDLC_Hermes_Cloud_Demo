# One-command deployment and destruction / 一条命令部署与销毁

> Language / 语言: **English / 中文** | [Português (Brasil)](IMPLANTACAO_UM_COMANDO_PT_BR.md)

This guide is intentionally short. The deployment command prepares the workstation tools, creates Huawei Cloud resources and deploys the complete AIDLC Demo. / 本指导刻意保持简洁。部署命令会自动准备工作站工具、创建华为云资源并部署完整的 AIDLC Demo。

## Before you start / 开始前

You only need: / 只需要：

- Windows 10/11 with Windows PowerShell 5.1 or PowerShell 7. / Windows 10/11，以及 Windows PowerShell 5.1 或 PowerShell 7。
- Outbound internet access. / 可访问公网。
- A Huawei Cloud account with permission and quota to create VPC, EIP, CCE, ECS/EVS, DCS and SWR resources in `sa-brazil-1`. / 华为云账号在 `sa-brazil-1` 具备创建 VPC、EIP、CCE、ECS/EVS、DCS 和 SWR 的权限及配额。
- A Hong Kong ModelArts Studio MaaS GLM-5.2 API key. / 香港 ModelArts Studio MaaS GLM-5.2 API Key。
- Your own GitHub application repository and fine-grained token. / 用户自己的 GitHub 业务仓与 Fine-grained Token。

You do **not** need to install Terraform, kubectl, Helm, KooCLI or Docker Desktop manually. / **不需要**手工安装 Terraform、kubectl、Helm、KooCLI 或 Docker Desktop。

## 1. Clone the framework repository / Clone 框架仓到本地

Open PowerShell and check whether Git is available: / 打开 PowerShell，检查 Git 是否可用：

```powershell
git --version
```

If Git is not found, install it once and reopen PowerShell: / 如果找不到 Git，安装一次并重新打开 PowerShell：

```powershell
winget install --id Git.Git -e --source winget
```

Clone the AIDLC framework into a short local path: / 把 AIDLC 框架仓 Clone 到较短的本地路径：

```powershell
New-Item -ItemType Directory -Path "C:\aidlc" -Force | Out-Null
Set-Location "C:\aidlc"
git clone https://github.com/seancjxu-ship-it/AIDLC_Hermes_Cloud_Demo.git
Set-Location "C:\aidlc\AIDLC_Hermes_Cloud_Demo"
```

The framework repository is public, so this clone operation does not require a GitHub token. / 框架仓是公共仓，本次 Clone 不需要 GitHub Token。

If the framework repository already exists locally, update it instead of cloning it again: / 如果本地已经存在框架仓，不要重复 Clone，执行更新：

```powershell
Set-Location "C:\aidlc\AIDLC_Hermes_Cloud_Demo"
git pull
```

## 2. Prepare the customer GitHub input / 准备客户 GitHub 输入

The framework repository above is the deployment program. The application repository is a separate repository that the Agents modify. / 上面的框架仓是部署程序；业务仓是 Agent 实际修改的另一个仓库。

1. Open [AIDLC_Simple_Order_Demo](https://github.com/seancjxu-ship-it/AIDLC_Simple_Order_Demo) in the browser. / 在浏览器打开示例业务仓。
2. Click **Fork** and create a copy under the deploying user's GitHub account. / 点击 **Fork**，在当前部署用户自己的 GitHub 账号下创建副本。
3. Record the fork URL, for example `https://github.com/<user>/AIDLC_Simple_Order_Demo`. / 记录 Fork 地址。
4. In GitHub, open **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**. / 在 GitHub 中打开 **Settings > Developer settings > Personal access tokens > Fine-grained tokens > Generate new token**。
5. Select the deploying user as **Resource owner**, choose **Only select repositories**, and select the fork created above. / Resource owner 选择当前部署用户，Repository access 选择 **Only select repositories**，再选择刚才的 Fork。
6. Set repository permissions to **Contents: Read and write** and **Pull requests: Read and write**, generate the token and copy it securely. / Repository permissions 设置为 **Contents: Read and write** 和 **Pull requests: Read and write**，生成 Token 并安全保存。

The token belongs to the deploying user and is scoped to that user's fork. Never use or share the original repository owner's token. / Token 属于当前部署用户，只授权其自己的 Fork。不要使用或传播原仓所有者的 Token。

## 3. Deploy with one command / 使用一条命令部署

Open PowerShell in the repository root and run: / 在仓库根目录打开 PowerShell，执行：

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1"
```

The command asks for the following values interactively: / 命令会交互式询问：

| Input / 输入 | What to enter / 输入内容 |
|---|---|
| Customer application repository / 客户业务仓 | The URL of the user's own fork, for example `https://github.com/<user>/AIDLC_Simple_Order_Demo`. / 用户自己的 Fork 地址。 |
| Huawei Cloud AK/SK / 华为云 AK/SK | Credentials with the required Brazil-region permissions. / 具备巴西区域所需权限的凭证。 |
| MaaS API Key | Hong Kong GLM-5.2 API Key. / 香港 GLM-5.2 API Key。 |
| GitHub Token | The deploying user's own token for the application repository. / 当前部署用户针对业务仓创建的 Token。 |

The GitHub token must grant the application repository **Contents: Read and write** and **Pull requests: Read and write**. Do not use the original repository owner's token. / GitHub Token 必须对业务仓具备 **Contents: Read and write** 与 **Pull requests: Read and write** 权限。不要使用原仓所有者的 Token。

Example input sequence; values in angle brackets are placeholders and must be replaced: / 输入顺序示例；尖括号内容是占位符，必须替换：

```text
Customer application GitHub repository URL:
https://github.com/<user>/AIDLC_Simple_Order_Demo

Huawei Cloud Access Key:
<your-huawei-cloud-ak>

Huawei Cloud Secret Key:
<your-huawei-cloud-sk>

ModelArts MaaS API Key (Hong Kong GLM-5.2):
<your-maas-api-key>

GitHub Token:
<your-own-fine-grained-token>
```

The SK, MaaS API Key and GitHub Token inputs are hidden while typing. They are injected into the deployment but are not written into the Git repository. / SK、MaaS API Key 和 GitHub Token 在输入时不会显示明文；它们会注入部署环境，但不会写入 Git 仓库。

## What the command does automatically / 命令自动完成什么

1. Downloads Terraform, kubectl, Helm and Huawei Cloud KooCLI into the Git-ignored `.tools` directory. / 把 Terraform、kubectl、Helm 和华为云 KooCLI 下载到 Git 已忽略的 `.tools` 目录。
2. Downloads and installs Docker Desktop for the current user when it is absent, starts it and waits for the Docker Engine. / 缺少 Docker Desktop 时自动下载、为当前用户安装、启动并等待 Docker Engine。
3. Creates VPC, subnet, security group, EIPs, CCE, one worker/ECS, DCS Redis and private SWR repositories in Brazil. / 在巴西创建 VPC、子网、安全组、EIP、CCE、一个 Worker/ECS、DCS Redis 和私有 SWR 仓库。
4. Builds the AIDLC platform image and pushes it to SWR. / 构建 AIDLC 平台镜像并推送到 SWR。
5. Deploys API, Orchestrator, Dev, QA, Review and Deploy Pods with Helm. / 通过 Helm 部署 API、Orchestrator、Dev、QA、Review 和 Deploy Pod。
6. Verifies all Pods and the public health endpoint. / 验证全部 Pod 与公网健康检查接口。

Docker Desktop's first installation may display a license, WSL 2, administrator-approval or Windows-restart prompt. Complete the displayed system prompt and run the same command again if Windows requests a restart. / Docker Desktop 首次安装时可能显示许可、WSL 2、管理员授权或 Windows 重启提示。按界面完成系统操作；如果 Windows 要求重启，重启后再次执行同一条命令即可。

## Successful result / 部署成功结果

The final output contains: / 最终输出包括：

- Console URL: `http://<node-eip>:30080` / Console 地址
- Login: `demo / huawei123` / 登录账号
- Region: Brazil `sa-brazil-1` / 巴西区域
- MaaS: Hong Kong `ap-southeast-1`, model `glm-5.2` / 香港 MaaS

## Check status / 查看状态

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\status.ps1"
```

## Destroy the Demo / 销毁 Demo

```powershell
powershell -ExecutionPolicy Bypass -File ".\scripts\cloud\destroy.ps1"
```

Type `DESTROY` when prompted. The command removes Preview workloads, the Kubernetes namespace, SWR image tags and all Terraform-managed Demo resources. / 按提示输入 `DESTROY`。命令会删除 Preview 工作负载、Kubernetes Namespace、SWR 镜像标签以及 Terraform 管理的全部 Demo 资源。

## Optional parameters / 可选参数

Pass the user's fork directly without waiting for the prompt: / 直接传入用户 Fork 地址：

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -RepositoryUrl "https://github.com/<user>/AIDLC_Simple_Order_Demo"
```

Restrict Console access to the customer's public IP: / 仅允许客户公网 IP 访问 Console：

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -AllowedConsoleCidr "203.0.113.10/32"
```

For centrally managed corporate workstations, IT may install Docker Desktop first and disable automatic Docker installation: / 如果企业工作站由 IT 统一管理，可先由 IT 安装 Docker Desktop，并禁用自动安装：

```powershell
powershell -ExecutionPolicy Bypass -File ".\deploy-demo.ps1" -SkipDockerDesktopInstall
```

## Demo boundary / Demo 边界

This is a low-cost demonstration environment with one CCE worker and single-node Redis. It does not include multi-AZ, backup, disaster recovery or production-grade identity integration. / 这是低成本演示环境，采用一个 CCE Worker 与单节点 Redis，不包含多可用区、备份、容灾或生产级身份集成。
