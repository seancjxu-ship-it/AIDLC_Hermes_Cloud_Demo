Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-AidlcRepoRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "..\.."))
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Content
    )
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Content, $encoding)
}

function Get-PlainText {
    param([Parameter(Mandatory = $true)][Security.SecureString]$SecureValue)
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Get-FirstNonEmptyEnvironmentVariable {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string[]]$Names
    )
    foreach ($name in $Names) {
        $value = [Environment]::GetEnvironmentVariable($name, "Process")
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
    }
    return $null
}

function Get-RequiredSecret {
    param(
        [Parameter(Mandatory = $true)][string]$EnvironmentName,
        [string[]]$EnvironmentAliases = @(),
        [Parameter(Mandatory = $true)][string]$Prompt
    )
    $value = Get-FirstNonEmptyEnvironmentVariable -Names (@($EnvironmentName) + $EnvironmentAliases)
    if (-not [string]::IsNullOrWhiteSpace($value)) {
        return $value
    }
    return Get-PlainText (Read-Host $Prompt -AsSecureString)
}

function Set-HuaweiCloudCredentialEnvironment {
    param(
        [Parameter(Mandatory = $true)][string]$AccessKey,
        [Parameter(Mandatory = $true)][string]$SecretKey,
        [Parameter(Mandatory = $true)][string]$Region
    )
    $values = @{
        HW_ACCESS_KEY          = $AccessKey
        HW_SECRET_KEY          = $SecretKey
        HW_REGION_NAME         = $Region
        HUAWEICLOUD_ACCESS_KEY = $AccessKey
        HUAWEICLOUD_SECRET_KEY = $SecretKey
        HUAWEICLOUD_REGION     = $Region
    }
    foreach ($entry in $values.GetEnumerator()) {
        [Environment]::SetEnvironmentVariable($entry.Key, $entry.Value, "Process")
    }
}

function Assert-LastExitCode {
    param([Parameter(Mandatory = $true)][string]$Message)
    if ($LASTEXITCODE -ne 0) {
        throw $Message
    }
}

function New-SafeTempDirectory {
    $base = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $path = Join-Path $base ("aidlc-cloud-" + [guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($path) | Out-Null
    return $path
}

function Remove-SafeTempDirectory {
    param([Parameter(Mandatory = $true)][string]$Path)
    $base = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    $resolved = [System.IO.Path]::GetFullPath($Path)
    if (-not $resolved.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a directory outside the system temporary directory: $resolved"
    }
    if (-not ([System.IO.Path]::GetFileName($resolved)).StartsWith("aidlc-cloud-")) {
        throw "Refusing to remove an unexpected temporary directory: $resolved"
    }
    if (Test-Path -LiteralPath $resolved) {
        Remove-Item -LiteralPath $resolved -Recurse -Force
    }
}

function ConvertTo-Base64Utf8 {
    param([AllowEmptyString()][string]$Value)
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Value))
}

function ConvertTo-YamlQuoted {
    param([AllowEmptyString()][string]$Value)
    return "'" + $Value.Replace("'", "''") + "'"
}

function Add-LocalToolsToPath {
    param([Parameter(Mandatory = $true)][string]$RepoRoot)
    $toolsPath = Join-Path $RepoRoot ".tools"
    if (Test-Path -LiteralPath $toolsPath) {
        $env:PATH = $toolsPath + [IO.Path]::PathSeparator + $env:PATH
    }
}

function Assert-Command {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$InstallHint = ""
    )
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        $message = "Required command '$Name' was not found."
        if ($InstallHint) { $message += " $InstallHint" }
        throw $message
    }
}
