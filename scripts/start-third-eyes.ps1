param([int]$Port = 8790)
$ErrorActionPreference = 'Stop'
$thirdEyesRoot = Split-Path -Parent $PSScriptRoot
$thirdEyesPython = Join-Path $thirdEyesRoot '.venv\Scripts\python.exe'
$thirdEyesConfig = Join-Path $thirdEyesRoot 'third-eyes.json'
$thirdEyesState = Join-Path $thirdEyesRoot '.third-eyes'
if (-not (Test-Path -LiteralPath $thirdEyesPython)) { throw 'Project Python environment is missing.' }
New-Item -ItemType Directory -Path $thirdEyesState -Force | Out-Null
$thirdEyesTokenFile = Join-Path $thirdEyesState 'access-token'
if (-not (Test-Path -LiteralPath $thirdEyesTokenFile)) {
    $thirdEyesToken = & $thirdEyesPython -c 'import secrets; print(secrets.token_urlsafe(32))'
    [System.IO.File]::WriteAllText($thirdEyesTokenFile, $thirdEyesToken.Trim())
}
$env:THIRD_EYES_TOKEN = [System.IO.File]::ReadAllText($thirdEyesTokenFile).Trim()
Push-Location (Join-Path $thirdEyesRoot 'agent')
try {
    if (-not (Test-Path -LiteralPath $thirdEyesConfig)) {
        & $thirdEyesPython -m src.third_eyes --config $thirdEyesConfig init
        if ($LASTEXITCODE -ne 0) { throw 'Third Eyes configuration failed.' }
    }
    Write-Host "Dashboard: http://127.0.0.1:$Port/third-eyes/v1/dashboard"
    Write-Host "Local access token is stored at: $thirdEyesTokenFile"
    & $thirdEyesPython -m src.third_eyes --config $thirdEyesConfig serve --port $Port
} finally { Pop-Location }
