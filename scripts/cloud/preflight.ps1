[CmdletBinding()]
param(
    [switch]$SkipDockerDesktopInstall,
    [ValidateRange(30, 600)][int]$DockerStartTimeoutSeconds = 180,
    [string]$DockerDesktopDownloadUri = "https://desktop.docker.com/win/main/amd64/Docker%20Desktop%20Installer.exe"
)

$ErrorActionPreference = "Stop"
. (Join-Path $PSScriptRoot "common.ps1")

function Add-DockerCliToPath {
    $candidateDirectories = @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin"),
        (Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\resources\bin"),
        (Join-Path $env:ProgramFiles "Docker\Docker\resources\bin")
    )
    foreach ($directory in $candidateDirectories) {
        if ((Test-Path -LiteralPath $directory) -and
            -not (($env:PATH -split [IO.Path]::PathSeparator) -contains $directory)) {
            $env:PATH = $directory + [IO.Path]::PathSeparator + $env:PATH
        }
    }
}

function Get-DockerDesktopExecutable {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\Docker Desktop.exe"),
        (Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }
    return $null
}

function Install-DockerDesktopForCurrentUser {
    param([Parameter(Mandatory = $true)][string]$DownloadUri)

    $downloadDirectory = New-SafeTempDirectory
    try {
        $installerPath = Join-Path $downloadDirectory "Docker Desktop Installer.exe"
        Write-Host "Downloading Docker Desktop from the official site / 从官方网站下载 Docker Desktop..."
        Invoke-WebRequest -UseBasicParsing -Uri $DownloadUri -OutFile $installerPath
        Write-Host "Installing Docker Desktop for the current user / 为当前用户安装 Docker Desktop..."
        $process = Start-Process -FilePath $installerPath -ArgumentList @("install", "--user", "--quiet") -Wait -PassThru
        if ($process.ExitCode -ne 0) {
            throw "Docker Desktop installer exited with code $($process.ExitCode). / Docker Desktop 安装程序退出码为 $($process.ExitCode)。"
        }
    }
    finally {
        Remove-SafeTempDirectory -Path $downloadDirectory
    }
}

function Test-DockerEngine {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return $false
    }
    try {
        & docker version *> $null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

$repoRoot = Get-AidlcRepoRoot
& (Join-Path $PSScriptRoot "bootstrap-tools.ps1")
Add-LocalToolsToPath -RepoRoot $repoRoot

Assert-Command terraform
Assert-Command kubectl
Assert-Command helm
Assert-Command hcloud "Automatic KooCLI download failed. Check network access to the Huawei Cloud download site. / KooCLI 自动下载失败，请检查华为云下载站点的网络访问。"

Add-DockerCliToPath
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    if ($SkipDockerDesktopInstall) {
        throw "Docker Desktop is missing and automatic installation was skipped. / 未安装 Docker Desktop，且已跳过自动安装。"
    }
    Install-DockerDesktopForCurrentUser -DownloadUri $DockerDesktopDownloadUri
    Add-DockerCliToPath
}
Assert-Command docker "Docker Desktop installation did not expose docker.exe. Reopen PowerShell and retry. / Docker Desktop 安装后未找到 docker.exe，请重新打开 PowerShell 后重试。"

if (-not (Test-DockerEngine)) {
    $dockerDesktopExecutable = Get-DockerDesktopExecutable
    if ($dockerDesktopExecutable) {
        Write-Host "Starting Docker Desktop / 正在启动 Docker Desktop..."
        Start-Process -FilePath $dockerDesktopExecutable | Out-Null
    }

    Write-Host "Waiting for the Docker Engine / 等待 Docker Engine 就绪..."
    $deadline = (Get-Date).AddSeconds($DockerStartTimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-DockerEngine) {
            break
        }
        Start-Sleep -Seconds 5
    }
}

if (-not (Test-DockerEngine)) {
    throw @"
Docker Desktop is installed but the Docker Engine is not ready.
Open Docker Desktop, accept the license if prompted, complete WSL 2 setup or restart Windows if requested, and run this preflight command again.
/ Docker Desktop 已安装，但 Docker Engine 尚未就绪。
请打开 Docker Desktop，按提示接受许可、完成 WSL 2 配置或重启 Windows，然后重新执行本预检查命令。
"@
}

Write-Host "Preflight passed / 部署前检查通过。"
