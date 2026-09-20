[CmdletBinding()]
param(
    [string]$TerraformVersion = "1.14.9",
    [string]$KubectlVersion = "1.36.0",
    [string]$HelmVersion = "3.19.0",
    [string]$KooCliDownloadUri = "https://ap-southeast-3-hwcloudcli.obs.ap-southeast-3.myhuaweicloud.com/cli/latest/huaweicloud-cli-windows-amd64.zip"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-AidlcRepoRoot
$toolsDir = Join-Path $repoRoot ".tools"
$downloadDir = New-SafeTempDirectory
[System.IO.Directory]::CreateDirectory($toolsDir) | Out-Null

try {
    if (-not (Get-Command terraform -ErrorAction SilentlyContinue) -and -not (Test-Path (Join-Path $toolsDir "terraform.exe"))) {
        Write-Host "Downloading Terraform / 下载 Terraform..."
        $zip = Join-Path $downloadDir "terraform.zip"
        Invoke-WebRequest -UseBasicParsing -Uri "https://releases.hashicorp.com/terraform/$TerraformVersion/terraform_${TerraformVersion}_windows_amd64.zip" -OutFile $zip
        Expand-Archive -LiteralPath $zip -DestinationPath $toolsDir -Force
    }

    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue) -and -not (Test-Path (Join-Path $toolsDir "kubectl.exe"))) {
        Write-Host "Downloading kubectl / 下载 kubectl..."
        Invoke-WebRequest -UseBasicParsing -Uri "https://dl.k8s.io/release/v$KubectlVersion/bin/windows/amd64/kubectl.exe" -OutFile (Join-Path $toolsDir "kubectl.exe")
    }

    if (-not (Get-Command helm -ErrorAction SilentlyContinue) -and -not (Test-Path (Join-Path $toolsDir "helm.exe"))) {
        Write-Host "Downloading Helm / 下载 Helm..."
        $zip = Join-Path $downloadDir "helm.zip"
        $expanded = Join-Path $downloadDir "helm"
        Invoke-WebRequest -UseBasicParsing -Uri "https://get.helm.sh/helm-v${HelmVersion}-windows-amd64.zip" -OutFile $zip
        Expand-Archive -LiteralPath $zip -DestinationPath $expanded -Force
        Copy-Item -LiteralPath (Join-Path $expanded "windows-amd64\helm.exe") -Destination (Join-Path $toolsDir "helm.exe") -Force
    }

    if (-not (Get-Command hcloud -ErrorAction SilentlyContinue) -and -not (Test-Path (Join-Path $toolsDir "hcloud.exe"))) {
        Write-Host "Downloading Huawei Cloud KooCLI / 下载华为云 KooCLI..."
        $zip = Join-Path $downloadDir "koocli.zip"
        $expanded = Join-Path $downloadDir "koocli"
        Invoke-WebRequest -UseBasicParsing -Uri $KooCliDownloadUri -OutFile $zip
        Expand-Archive -LiteralPath $zip -DestinationPath $expanded -Force
        $hcloudExecutable = Get-ChildItem -LiteralPath $expanded -Filter "hcloud.exe" -File -Recurse |
            Select-Object -First 1
        if (-not $hcloudExecutable) {
            throw "The official KooCLI archive did not contain hcloud.exe. / 官方 KooCLI 压缩包中未找到 hcloud.exe。"
        }
        Copy-Item -LiteralPath $hcloudExecutable.FullName -Destination (Join-Path $toolsDir "hcloud.exe") -Force
    }

    Write-Host "Portable tools are ready / 便携工具已就绪: $toolsDir"
}
finally {
    Remove-SafeTempDirectory -Path $downloadDir
}
