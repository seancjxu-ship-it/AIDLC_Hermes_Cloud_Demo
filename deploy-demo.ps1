[CmdletBinding()]
param(
    [string]$RepositoryUrl,
    [string]$AllowedConsoleCidr,
    [switch]$SkipDockerDesktopInstall
)

$ErrorActionPreference = "Stop"
$deployScript = Join-Path $PSScriptRoot "scripts\cloud\deploy.ps1"

Write-Host "AIDLC Demo one-command deployment / AIDLC Demo 一条命令部署"
& $deployScript @PSBoundParameters
