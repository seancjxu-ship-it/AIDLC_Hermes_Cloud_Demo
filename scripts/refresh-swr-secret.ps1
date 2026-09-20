[CmdletBinding()]
param(
    [string]$Region = "sa-brazil-1",
    [string]$ClusterId = "83ce4753-b311-11f1-9614-0255ac1000b6",
    [string]$Namespace = "aidlc-demo",
    [string]$SecretName = "swr-pull"
)

$ErrorActionPreference = "Stop"

function ConvertFrom-Utf8Base64 {
    param([Parameter(Mandatory = $true)][string]$Value)
    return [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($Value))
}

$cnRequest = ConvertFrom-Utf8Base64 "6I635Y+WIFNXUiDkuLTml7blh63or4EuLi4="
$cnRequestFail = ConvertFrom-Utf8Base64 "6I635Y+WIFNXUiDlh63or4HlpLHotKXjgII="
$cnAuthMissing = ConvertFrom-Utf8Base64 "U1dSIOWTjeW6lOe8uuWwkSBhdXRocyDlrZfmrrXjgII="
$cnKubeconfig = ConvertFrom-Utf8Base64 "5Yib5bu65Li05pe2IENDRSBrdWJlY29uZmlnLi4u"
$cnKubeconfigFail = ConvertFrom-Utf8Base64 "5Yib5bu6IENDRSBrdWJlY29uZmlnIOWksei0peOAgg=="
$cnSecret = ConvertFrom-Utf8Base64 "5pu05pawIEt1YmVybmV0ZXMgU2VjcmV0Li4u"
$cnSecretGenerateFail = ConvertFrom-Utf8Base64 "55Sf5oiQIEt1YmVybmV0ZXMgU2VjcmV0IOWksei0peOAgg=="
$cnSecretApplyFail = ConvertFrom-Utf8Base64 "5bqU55SoIEt1YmVybmV0ZXMgU2VjcmV0IOWksei0peOAgg=="
$cnSuccess = ConvertFrom-Utf8Base64 "U1dSIOWHreivgeWIt+aWsOaIkOWKn+OAguWHreivgeacquaJk+WNsO+8jOS5n+acquWGmeWFpeS7o+eggeS7k+OAgg=="

$workDir = Join-Path ([System.IO.Path]::GetTempPath()) ("aidlc-swr-" + [guid]::NewGuid().ToString("N"))
$dockerConfigPath = Join-Path $workDir "config.json"
$kubeConfigPath = Join-Path $workDir "kubeconfig.yaml"
$secretManifestPath = Join-Path $workDir "swr-pull-secret.yaml"

New-Item -ItemType Directory -Path $workDir | Out-Null

try {
    Write-Host ("[1/3] Requesting a temporary SWR credential / " + $cnRequest)
    $responseLines = & hcloud SWR CreateAuthorizationToken --cli-region=$Region
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to request the SWR credential / " + $cnRequestFail)
    }

    $responseText = $responseLines -join [Environment]::NewLine
    $dockerConfig = $responseText | ConvertFrom-Json
    if (-not $dockerConfig.auths) {
        throw ("The SWR response does not contain an auths object / " + $cnAuthMissing)
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $dockerConfigJson = $dockerConfig | ConvertTo-Json -Depth 10 -Compress
    [System.IO.File]::WriteAllText($dockerConfigPath, $dockerConfigJson, $utf8NoBom)

    Write-Host ("[2/3] Creating a temporary CCE kubeconfig / " + $cnKubeconfig)
    & hcloud CCE update-kubeconfig --cluster-id $ClusterId --region $Region --external --output $kubeConfigPath
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to create the CCE kubeconfig / " + $cnKubeconfigFail)
    }

    Write-Host ("[3/3] Updating Kubernetes Secret '" + $SecretName + "' / " + $cnSecret)
    $secretYaml = & kubectl --kubeconfig $kubeConfigPath -n $Namespace create secret generic $SecretName `
        --type=kubernetes.io/dockerconfigjson `
        --from-file=.dockerconfigjson=$dockerConfigPath `
        --dry-run=client -o yaml
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to generate the Kubernetes Secret / " + $cnSecretGenerateFail)
    }

    [System.IO.File]::WriteAllText(
        $secretManifestPath,
        ($secretYaml -join [Environment]::NewLine),
        $utf8NoBom
    )
    & kubectl --kubeconfig $kubeConfigPath apply -f $secretManifestPath
    if ($LASTEXITCODE -ne 0) {
        throw ("Failed to apply the Kubernetes Secret / " + $cnSecretApplyFail)
    }

    Write-Host "SWR credential refreshed successfully. No credential was printed or stored in the repository."
    Write-Host $cnSuccess
}
finally {
    if (Test-Path -LiteralPath $workDir) {
        Remove-Item -LiteralPath $workDir -Recurse -Force
    }
}

