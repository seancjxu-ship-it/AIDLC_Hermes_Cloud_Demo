[CmdletBinding()]
param([switch]$Force)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-AidlcRepoRoot
$terraformDir = Join-Path $repoRoot "infra\terraform"
$deploymentFile = Join-Path $repoRoot ".aidlc-deployment.json"
$workDir = New-SafeTempDirectory

try {
    Add-LocalToolsToPath -RepoRoot $repoRoot
    Assert-Command terraform
    Assert-Command hcloud

    if (-not (Test-Path -LiteralPath $deploymentFile)) {
        throw "No .aidlc-deployment.json was found. Destruction is intentionally blocked to avoid targeting the wrong stack. / 未找到 .aidlc-deployment.json；为避免误删错误环境，已阻止销毁。"
    }
    $record = Get-Content -Raw -LiteralPath $deploymentFile | ConvertFrom-Json
    if (-not $Force) {
        $answer = Read-Host "Type DESTROY to remove the AIDLC Demo in $($record.region) / 输入 DESTROY 销毁 $($record.region) 的 AIDLC Demo"
        if ($answer -cne "DESTROY") {
            Write-Host "Cancelled / 已取消。"
            exit 0
        }
    }

    $accessKey = Get-FirstNonEmptyEnvironmentVariable -Names @("HW_ACCESS_KEY", "HUAWEICLOUD_ACCESS_KEY")
    if ([string]::IsNullOrWhiteSpace($accessKey)) { $accessKey = Read-Host "Huawei Cloud Access Key / 华为云 AK" }
    $secretKey = Get-RequiredSecret `
        -EnvironmentName "HW_SECRET_KEY" `
        -EnvironmentAliases @("HUAWEICLOUD_SECRET_KEY") `
        -Prompt "Huawei Cloud Secret Key / 华为云 SK"
    Set-HuaweiCloudCredentialEnvironment -AccessKey $accessKey -SecretKey $secretKey -Region $record.region

    if (Get-Command kubectl -ErrorAction SilentlyContinue) {
        Push-Location $terraformDir
        try { $kubeConfig = (& terraform output -raw kube_config_raw) -join [Environment]::NewLine }
        finally { Pop-Location }
        if ($kubeConfig) {
            $kubeConfigPath = Join-Path $workDir "kubeconfig.yaml"
            Write-Utf8NoBom -Path $kubeConfigPath -Content $kubeConfig
            if (Get-Command helm -ErrorAction SilentlyContinue) {
                & helm uninstall aidlc-factory --namespace $record.namespace --kubeconfig $kubeConfigPath --wait 2>$null
            }
            & kubectl --kubeconfig $kubeConfigPath delete namespace $record.namespace --ignore-not-found=true --wait=true --timeout=10m 2>$null
        }
    }

    Write-Host "Removing SWR image tags before repository deletion / 删除 SWR 仓库前清理镜像标签..."
    $hcloudAuth = @(
        "--cli-region=$($record.region)",
        "--cli-access-key=$accessKey",
        "--cli-secret-key=$secretKey",
        "--cli-mode=AKSK",
        "--cli-output=json"
    )
    foreach ($repository in @("aidlc-factory", "order-demo")) {
        $response = & hcloud SWR ListRepositoryTags "--namespace=$($record.swr_organization)" "--repository=$repository" --limit=1000 --offset=0 @hcloudAuth 2>$null
        if ($LASTEXITCODE -eq 0 -and $response) {
            $parsed = ($response -join [Environment]::NewLine) | ConvertFrom-Json
            $items = if ($parsed -is [array]) { $parsed } elseif ($parsed.tags) { $parsed.tags } else { @() }
            foreach ($item in $items) {
                $tagName = if ($item.tag) { $item.tag } elseif ($item.name) { $item.name } else { $null }
                if ($tagName) {
                    & hcloud SWR DeleteRepoTag "--namespace=$($record.swr_organization)" "--repository=$repository" "--tag=$tagName" @hcloudAuth | Out-Null
                }
            }
        }
    }

    Write-Host "Destroying Huawei Cloud resources with Terraform / 使用 Terraform 销毁华为云资源..."
    Push-Location $terraformDir
    try {
        & terraform destroy -auto-approve `
            "-var=region=$($record.region)" `
            "-var=availability_zone=$($record.availability_zone)" `
            "-var=prefix=$($record.prefix)" `
            "-var=swr_organization=$($record.swr_organization)"
        Assert-LastExitCode "terraform destroy failed / terraform destroy 失败。"
    }
    finally { Pop-Location }

    Remove-Item -LiteralPath $deploymentFile -Force
    Write-Host "All demo resources managed by this state were destroyed / 此 Terraform State 管理的 Demo 资源已全部销毁。"
}
finally {
    $accessKey = $null
    $secretKey = $null
    Remove-SafeTempDirectory -Path $workDir
}
