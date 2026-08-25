[CmdletBinding()]
param(
    [string]$Python = "py -3.11",
    [string]$CoreVersion = "0.6.3"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvRoot = Join-Path $repoRoot ".venv"
$venvPython = Join-Path $venvRoot "Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    Push-Location $repoRoot
    try {
        if ($Python -eq "py -3.11") {
            & py -3.11 -m venv .venv
        }
        else {
            & $Python -m venv .venv
        }
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create .venv."
        }
    }
    finally {
        Pop-Location
    }
}

$repairPip = Join-Path $PSScriptRoot "repair_pip_residue.py"
& $venvPython $repairPip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to repair interrupted pip-upgrade residue."
}

& $venvPython -m ensurepip --upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Failed to ensure pip is available in .venv."
}

$coreName = "pds_core-$CoreVersion-py3-none-any.whl"
$coreWheel = Join-Path ([System.IO.Path]::GetTempPath()) $coreName
$coreUri = "https://github.com/Paper-Data-Suite/pds-core/releases/download/v$CoreVersion/$coreName"

Invoke-WebRequest -Uri $coreUri -OutFile $coreWheel -ErrorAction Stop
& $venvPython (Join-Path $PSScriptRoot "verify_core_wheel.py") $coreWheel
if ($LASTEXITCODE -ne 0) {
    throw "Core wheel verification failed."
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Failed to upgrade pip. Re-run bootstrap_dev.ps1; interrupted pip residue will be repaired automatically."
}

& $venvPython -m pip install $coreWheel
if ($LASTEXITCODE -ne 0) {
    throw "Failed to install the authenticated Core wheel."
}

Push-Location $repoRoot
try {
    & $venvPython -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install Portia development dependencies."
    }
    & $venvPython -m pip check
    if ($LASTEXITCODE -ne 0) {
        throw "Portia development environment has broken requirements."
    }
}
finally {
    Pop-Location
}

Write-Host "Portia development environment is ready."
Write-Host "Authenticated Core wheel: $coreWheel"
Write-Host "Activate it with: .\.venv\Scripts\Activate.ps1"
