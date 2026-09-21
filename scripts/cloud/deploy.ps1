[CmdletBinding()]
param(
    [string]$Region = "sa-brazil-1",
    [string]$AvailabilityZone = "sa-brazil-1b",
    [string]$Prefix = "aidlc-demo",
    [string]$Namespace = "aidlc-demo",
    [string]$SWROrganization = "aidlc-demo",
    [string]$PlatformTag = "4.0.0",
    [string]$RepositoryUrl = "",
    [string]$DefaultBranch = "main",
    [string]$MaaSBaseUrl = "https://api-ap-southeast-1.modelarts-maas.com/openai/v1",
    [string]$MaaSModel = "glm-5.2",
    [string]$DemoUsername = "demo",
    [string]$DemoPassword = "huawei123",
    [string]$AllowedConsoleCidr = "0.0.0.0/0",
    [switch]$SkipDockerDesktopInstall,
    [ValidateRange(30, 600)][int]$DockerStartTimeoutSeconds = 180,
    [switch]$SkipToolBootstrap
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-AidlcRepoRoot
$terraformDir = Join-Path $repoRoot "infra\terraform"
$chartDir = Join-Path $repoRoot "deploy\helm\aidlc-factory"
$deploymentFile = Join-Path $repoRoot ".aidlc-deployment.json"
$workDir = New-SafeTempDirectory

try {
    if (-not $SkipToolBootstrap) {
        Write-Host "Preparing workstation tools and Docker / 准备工作站工具与 Docker..."
        & (Join-Path $PSScriptRoot "preflight.ps1") `
            -SkipDockerDesktopInstall:$SkipDockerDesktopInstall `
            -DockerStartTimeoutSeconds $DockerStartTimeoutSeconds
    }
    Add-LocalToolsToPath -RepoRoot $repoRoot
    Assert-Command terraform
    Assert-Command kubectl
    Assert-Command helm
    Assert-Command hcloud "Install Huawei Cloud KooCLI. / 请安装华为云 KooCLI。"
    Assert-Command docker "Start Docker Desktop. / 请启动 Docker Desktop。"

    & docker version *> $null
    Assert-LastExitCode "Docker Engine is not reachable. / 无法连接 Docker Engine。"

    if ([string]::IsNullOrWhiteSpace($RepositoryUrl)) {
        $RepositoryUrl = Read-Host "Customer application GitHub repository URL (use your own fork) / 客户业务 GitHub 仓库地址（请使用自己的 Fork）"
    }
    if ([string]::IsNullOrWhiteSpace($RepositoryUrl)) {
        throw "Customer application repository URL cannot be empty. / 客户业务代码仓地址不能为空。"
    }

    $accessKey = Get-FirstNonEmptyEnvironmentVariable -Names @("HW_ACCESS_KEY", "HUAWEICLOUD_ACCESS_KEY")
    if ([string]::IsNullOrWhiteSpace($accessKey)) {
        $accessKey = Read-Host "Huawei Cloud Access Key / 华为云 AK"
    }
    $secretKey = Get-RequiredSecret `
        -EnvironmentName "HW_SECRET_KEY" `
        -EnvironmentAliases @("HUAWEICLOUD_SECRET_KEY") `
        -Prompt "Huawei Cloud Secret Key / 华为云 SK"
    $maasApiKey = Get-RequiredSecret -EnvironmentName "AIDLC_MAAS_API_KEY" -Prompt "ModelArts MaaS API Key (Hong Kong GLM-5.2) / 香港 GLM-5.2 MaaS API Key"
    $githubToken = Get-RequiredSecret -EnvironmentName "AIDLC_GITHUB_TOKEN" -Prompt "GitHub token with Contents and Pull requests read/write / GitHub Token（Contents 与 Pull requests 读写）"

    if ([string]::IsNullOrWhiteSpace($accessKey) -or [string]::IsNullOrWhiteSpace($secretKey)) {
        throw "Huawei Cloud AK/SK cannot be empty. / 华为云 AK/SK 不能为空。"
    }

    Set-HuaweiCloudCredentialEnvironment -AccessKey $accessKey -SecretKey $secretKey -Region $Region

    Write-Host "[1/7] Provisioning Huawei Cloud infrastructure with Terraform / 使用 Terraform 创建华为云资源..."
    Push-Location $terraformDir
    try {
        & terraform init -upgrade
        Assert-LastExitCode "terraform init failed / terraform init 失败。"
        & terraform apply -auto-approve `
            "-var=region=$Region" `
            "-var=availability_zone=$AvailabilityZone" `
            "-var=prefix=$Prefix" `
            "-var=swr_organization=$SWROrganization" `
            "-var=allowed_console_cidr=$AllowedConsoleCidr"
        Assert-LastExitCode "terraform apply failed / terraform apply 失败。"

        $clusterId = (& terraform output -raw cluster_id) -join ""
        $nodePublicIp = (& terraform output -raw node_public_ip) -join ""
        $platformRepository = (& terraform output -raw platform_image_repository) -join ""
        $applicationRepository = (& terraform output -raw application_image_repository) -join ""
        $redisUrl = (& terraform output -raw redis_url) -join ""
        $kubeConfig = (& terraform output -raw kube_config_raw) -join [Environment]::NewLine
    }
    finally {
        Pop-Location
    }

    $kubeConfigPath = Join-Path $workDir "kubeconfig.yaml"
    $dockerConfigPath = Join-Path $workDir "config.json"
    $swrSecretPath = Join-Path $workDir "swr-pull.json"
    $appSecretPath = Join-Path $workDir "aidlc-secrets.json"
    $helmValuesPath = Join-Path $workDir "values.generated.yaml"
    Write-Utf8NoBom -Path $kubeConfigPath -Content $kubeConfig

    Write-Host "[2/7] Requesting a temporary SWR credential / 获取临时 SWR 凭证..."
    $hcloudAuth = @(
        "--cli-region=$Region",
        "--cli-access-key=$accessKey",
        "--cli-secret-key=$secretKey",
        "--cli-mode=AKSK",
        "--cli-output=json"
    )
    $authResponse = & hcloud SWR CreateAuthorizationToken @hcloudAuth
    Assert-LastExitCode "Failed to obtain the SWR credential / 获取 SWR 凭证失败。"
    $dockerConfig = (($authResponse -join [Environment]::NewLine) | ConvertFrom-Json)
    if (-not $dockerConfig.auths) {
        throw "The SWR response does not contain a Docker auths object. / SWR 响应中没有 Docker auths 对象。"
    }
    Write-Utf8NoBom -Path $dockerConfigPath -Content ($dockerConfig | ConvertTo-Json -Depth 20 -Compress)

    Write-Host "[3/7] Building and pushing the AIDLC platform image / 构建并推送 AIDLC 平台镜像..."
    $platformImage = "${platformRepository}:$PlatformTag"
    & docker --config $workDir build --pull -t $platformImage $repoRoot
    Assert-LastExitCode "Docker build failed / Docker 构建失败。"
    & docker --config $workDir push $platformImage
    Assert-LastExitCode "Docker push failed / Docker 推送失败。"

    Write-Host "[4/7] Creating Kubernetes namespace and secrets / 创建 Kubernetes Namespace 与 Secret..."
    & kubectl --kubeconfig $kubeConfigPath create namespace $Namespace --dry-run=client -o yaml | & kubectl --kubeconfig $kubeConfigPath apply -f -
    Assert-LastExitCode "Failed to create the namespace / 创建 Namespace 失败。"

    $swrSecretYaml = & kubectl --kubeconfig $kubeConfigPath -n $Namespace create secret generic swr-pull `
        --type=kubernetes.io/dockerconfigjson `
        "--from-file=.dockerconfigjson=$dockerConfigPath" `
        --dry-run=client -o json
    Assert-LastExitCode "Failed to generate the SWR pull secret / 生成 SWR 拉取凭证失败。"
    Write-Utf8NoBom -Path $swrSecretPath -Content ($swrSecretYaml -join [Environment]::NewLine)
    & kubectl --kubeconfig $kubeConfigPath apply -f $swrSecretPath
    Assert-LastExitCode "Failed to apply the SWR pull secret / 应用 SWR 拉取凭证失败。"

    $secretManifest = @{
        apiVersion = "v1"
        kind = "Secret"
        metadata = @{ name = "aidlc-secrets"; namespace = $Namespace }
        type = "Opaque"
        data = @{
            AIDLC_DEMO_USERNAME = ConvertTo-Base64Utf8 $DemoUsername
            AIDLC_DEMO_PASSWORD = ConvertTo-Base64Utf8 $DemoPassword
            GITHUB_TOKEN = ConvertTo-Base64Utf8 $githubToken
            MAAS_API_KEY = ConvertTo-Base64Utf8 $maasApiKey
        }
    }
    Write-Utf8NoBom -Path $appSecretPath -Content ($secretManifest | ConvertTo-Json -Depth 10)
    & kubectl --kubeconfig $kubeConfigPath apply -f $appSecretPath
    Assert-LastExitCode "Failed to apply application secrets / 应用业务 Secret 失败。"

    $values = @"
image:
  repository: $(ConvertTo-YamlQuoted $platformRepository)
  tag: $(ConvertTo-YamlQuoted $PlatformTag)
  pullPolicy: Always
service:
  type: NodePort
  port: 8000
  nodePort: 30080
config:
  redisUrl: $(ConvertTo-YamlQuoted $redisUrl)
  repositoryUrl: $(ConvertTo-YamlQuoted $RepositoryUrl)
  defaultBranch: $(ConvertTo-YamlQuoted $DefaultBranch)
  maasBaseUrl: $(ConvertTo-YamlQuoted $MaaSBaseUrl)
  maasModel: $(ConvertTo-YamlQuoted $MaaSModel)
  swrImageRepo: $(ConvertTo-YamlQuoted $applicationRepository)
  runtimeImage: $(ConvertTo-YamlQuoted $platformImage)
  kubernetesNamespace: $(ConvertTo-YamlQuoted $Namespace)
  imagePullSecret: swr-pull
  githubWrite: 'true'
secrets:
  create: false
"@
    Write-Utf8NoBom -Path $helmValuesPath -Content $values

    Write-Host "[5/7] Installing API, Orchestrator and four Agent Workers with Helm / 使用 Helm 安装 API、Orchestrator 与四类 Agent Worker..."
    & helm upgrade --install aidlc-factory $chartDir `
        --namespace $Namespace --create-namespace `
        --kubeconfig $kubeConfigPath `
        --values $helmValuesPath `
        --wait --timeout 15m
    Assert-LastExitCode "Helm installation failed / Helm 安装失败。"

    Write-Host "[6/7] Waiting for all AIDLC Pods / 等待全部 AIDLC Pod 就绪..."
    foreach ($deployment in @("aidlc-api", "hermes-orchestrator", "hermes-sf-dev", "hermes-sf-qa", "hermes-sf-review", "hermes-sf-deploy")) {
        & kubectl --kubeconfig $kubeConfigPath -n $Namespace rollout status "deployment/$deployment" --timeout=10m
        Assert-LastExitCode "Deployment $deployment did not become ready / Deployment $deployment 未就绪。"
    }

    $consoleUrl = "http://${nodePublicIp}:30080"
    $deploymentRecord = [ordered]@{
        region = $Region
        availability_zone = $AvailabilityZone
        prefix = $Prefix
        namespace = $Namespace
        swr_organization = $SWROrganization
        platform_tag = $PlatformTag
        cluster_id = $clusterId
        console_url = $consoleUrl
        repository_url = $RepositoryUrl
        deployed_at = (Get-Date).ToUniversalTime().ToString("o")
    }
    Write-Utf8NoBom -Path $deploymentFile -Content ($deploymentRecord | ConvertTo-Json -Depth 5)

    Write-Host "[7/7] Verifying the public health endpoint / 验证公网健康检查..."
    $healthy = $false
    for ($attempt = 1; $attempt -le 20; $attempt++) {
        try {
            $health = Invoke-RestMethod -Uri "$consoleUrl/health" -TimeoutSec 10
            if ($health.status -eq "ok") { $healthy = $true; break }
        }
        catch {
            Start-Sleep -Seconds 6
        }
    }
    if (-not $healthy) {
        throw "The Pods are ready, but the public health endpoint did not respond. Check the NodePort security-group CIDR. / Pod 已就绪，但公网健康检查失败，请检查 NodePort 安全组来源网段。"
    }

    Write-Host ""
    Write-Host "Deployment completed / 部署完成"
    Write-Host "Console / 控制台: $consoleUrl"
    Write-Host "Login / 登录: $DemoUsername / $DemoPassword"
}
finally {
    $accessKey = $null
    $secretKey = $null
    $maasApiKey = $null
    $githubToken = $null
    Remove-SafeTempDirectory -Path $workDir
}
