[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-AidlcRepoRoot
$terraformDir = Join-Path $repoRoot "infra\terraform"
$deploymentFile = Join-Path $repoRoot ".aidlc-deployment.json"
$workDir = New-SafeTempDirectory

try {
    Add-LocalToolsToPath -RepoRoot $repoRoot
    Assert-Command terraform
    Assert-Command kubectl
    if (-not (Test-Path -LiteralPath $deploymentFile)) {
        throw "No deployment record was found. Run deploy.ps1 first. / 未找到部署记录，请先运行 deploy.ps1。"
    }
    $record = Get-Content -Raw -LiteralPath $deploymentFile | ConvertFrom-Json
    Push-Location $terraformDir
    try {
        $kubeConfig = (& terraform output -raw kube_config_raw) -join [Environment]::NewLine
    }
    finally { Pop-Location }
    $kubeConfigPath = Join-Path $workDir "kubeconfig.yaml"
    Write-Utf8NoBom -Path $kubeConfigPath -Content $kubeConfig

    Write-Host "AIDLC deployment / AIDLC 部署状态"
    Write-Host "Console / 控制台: $($record.console_url)"
    & kubectl --kubeconfig $kubeConfigPath -n $record.namespace get deployments,pods,services -o wide
    Assert-LastExitCode "Unable to read Kubernetes status / 无法读取 Kubernetes 状态。"
}
finally {
    Remove-SafeTempDirectory -Path $workDir
}
