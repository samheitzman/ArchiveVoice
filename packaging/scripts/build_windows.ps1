$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..\..")

py -3 -m venv .venv-build
.\.venv-build\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[build]"

python -m PyInstaller --clean --noconfirm ArchiveVoice.spec

Write-Host "Built dist\Archive Voice\Archive Voice.exe"

