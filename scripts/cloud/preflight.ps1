[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

$repoRoot = Get-AidlcRepoRoot
& (Join-Path $PSScriptRoot "bootstrap-tools.ps1")
Add-LocalToolsToPath -RepoRoot $repoRoot

Assert-Command terraform
Assert-Command kubectl
Assert-Command helm
Assert-Command hcloud "Install Huawei Cloud KooCLI and put hcloud.exe in PATH. / 请安装华为云 KooCLI 并加入 PATH。"
Assert-Command docker "Start Docker Desktop before deployment. / 部署前请启动 Docker Desktop。"

& docker version *> $null
Assert-LastExitCode "Docker Engine is not reachable. Start Docker Desktop and retry. / 无法连接 Docker Engine，请启动 Docker Desktop 后重试。"

Write-Host "Preflight passed / 部署前检查通过。"
