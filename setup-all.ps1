# Full project setup (except Supabase keys)
# Run: powershell -ExecutionPolicy Bypass -File C:\Users\rkdgu\pokemon-card-price\setup-all.ps1

$ErrorActionPreference = "Continue"
$Root = "C:\Users\rkdgu\pokemon-card-price"
$Log = Join-Path $Root "setup-all.log"

function Log($msg) {
    $line = "[$(Get-Date -Format 'HH:mm:ss')] $msg"
    Write-Host $line
    Add-Content -Path $Log -Value $line
}

Set-Location $Root
"=== Setup started $(Get-Date) ===" | Out-File $Log

Log "=== 1. Check Node.js ==="
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Log "Node.js not found. Installing via winget..."
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements 2>&1 | Out-File $Log -Append
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
if (Get-Command node -ErrorAction SilentlyContinue) {
    Log ("node: " + (node --version))
    Log ("npm: " + (npm --version))
} else {
    Log "ERROR: Node.js still not available. Install from https://nodejs.org/"
}

Log "=== 2. Check Python ==="
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Log "Python not found. Installing via winget..."
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements 2>&1 | Out-File $Log -Append
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    Log ("python: " + (python --version 2>&1))
} else {
    Log "ERROR: Python still not available. Install from https://python.org/"
}

Log "=== 3. Create env files from examples ==="
$webEnv = Join-Path $Root "web\.env.local"
$webExample = Join-Path $Root "web\.env.example"
if (-not (Test-Path $webEnv) -and (Test-Path $webExample)) {
    Copy-Item $webExample $webEnv
    Log "Created web\.env.local (fill Supabase keys)"
} elseif (Test-Path $webEnv) {
    Log "web\.env.local already exists"
}

$crawlerEnv = Join-Path $Root "crawler\.env"
$crawlerExample = Join-Path $Root "crawler\.env.example"
if (-not (Test-Path $crawlerEnv) -and (Test-Path $crawlerExample)) {
    Copy-Item $crawlerExample $crawlerEnv
    Log "Created crawler\.env (fill Supabase keys)"
} elseif (Test-Path $crawlerEnv) {
    Log "crawler\.env already exists"
}

Log "=== 4. Web: npm install ==="
if (Get-Command npm -ErrorAction SilentlyContinue) {
    Set-Location (Join-Path $Root "web")
    npm install 2>&1 | Out-File $Log -Append
    if ($LASTEXITCODE -eq 0) {
        Log "npm install OK"
    } else {
        Log "npm install failed (see setup-all.log)"
    }
} else {
    Log "SKIP npm install (npm not found)"
}

Log "=== 5. Crawler: Python venv + pip install ==="
if (Get-Command python -ErrorAction SilentlyContinue) {
    Set-Location (Join-Path $Root "crawler")
    $venv = Join-Path (Get-Location) ".venv"
    if (-not (Test-Path $venv)) {
        python -m venv .venv 2>&1 | Out-File $Log -Append
        Log "Created crawler\.venv"
    } else {
        Log "crawler\.venv already exists"
    }

    $pip = Join-Path $venv "Scripts\pip.exe"
    $req = Join-Path (Get-Location) "requirements.txt"
    if (Test-Path $pip) {
        # asyncio is stdlib; skip if pip complains
        & $pip install --upgrade pip 2>&1 | Out-File $Log -Append
        & $pip install playwright==1.49.0 supabase==2.31.0 httpx==0.27.0 python-dotenv==1.0.1 2>&1 | Out-File $Log -Append
        if ($LASTEXITCODE -eq 0) {
            Log "pip install OK"
            & (Join-Path $venv "Scripts\python.exe") -m playwright install chromium 2>&1 | Out-File $Log -Append
            Log "playwright chromium install attempted"
        } else {
            Log "pip install failed (see setup-all.log)"
        }
    }
} else {
    Log "SKIP crawler venv (python not found)"
}

Set-Location $Root
Log "=== Done ==="
Log "Next: edit web\.env.local and crawler\.env with Supabase keys from dashboard"
Log "Then: cd web && npm run dev"
