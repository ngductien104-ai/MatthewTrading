param([ValidateRange(1, 60)][int]$Days = 30)
$ErrorActionPreference = 'Stop'

$shadowRoot = Split-Path -Parent $PSScriptRoot
$shadowPython = Join-Path $shadowRoot '.venv\Scripts\python.exe'
$shadowConfig = Join-Path $shadowRoot 'third-eyes.json'
$shadowState = Join-Path $shadowRoot '.third-eyes-shadow'
$shadowPidFile = Join-Path $shadowState 'process-id'

if (-not (Test-Path -LiteralPath $shadowPython)) { throw 'Project Python environment is missing.' }
if (-not (Test-Path -LiteralPath $shadowConfig)) { throw 'third-eyes.json is missing.' }
New-Item -ItemType Directory -Path $shadowState -Force | Out-Null

if (Test-Path -LiteralPath $shadowPidFile) {
    $existingPid = [int]([System.IO.File]::ReadAllText($shadowPidFile).Trim())
    if (Get-Process -Id $existingPid -ErrorAction SilentlyContinue) {
        throw "A Third Eyes shadow collector is already running with PID $existingPid."
    }
}

$shadowSources = @(
    'vn_cpi', 'us_policy_rate', 'usd_index', 'company_disclosures',
    'company_FPT_price', 'company_FPT_volume', 'company_FPT_profit', 'company_FPT_news',
    'company_HPG_price', 'company_HPG_volume', 'company_HPG_profit', 'company_HPG_news',
    'company_MWG_price', 'company_MWG_volume', 'company_MWG_profit', 'company_MWG_news'
)
$shadowArgs = @(
    '-u', '-m', 'agent.src.third_eyes', '--config', $shadowConfig, 'soak',
    '--seconds', ([string]($Days * 86400)), '--state-dir', $shadowState
)
foreach ($source in $shadowSources) {
    $shadowArgs += @('--source', $source)
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdout = Join-Path $shadowState "shadow-$stamp.out.log"
$stderr = Join-Path $shadowState "shadow-$stamp.err.log"
$process = Start-Process -FilePath $shadowPython -ArgumentList $shadowArgs `
    -WorkingDirectory $shadowRoot -WindowStyle Hidden `
    -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
[System.IO.File]::WriteAllText($shadowPidFile, [string]$process.Id)

[pscustomobject]@{
    mode = 'shadow'
    production = $false
    ai_enabled = $false
    api_enabled = $false
    duration_days = $Days
    process_id = $process.Id
    state_dir = $shadowState
    stdout = $stdout
    stderr = $stderr
}
