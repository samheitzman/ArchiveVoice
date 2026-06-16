#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python3 -m venv .venv-build
source .venv-build/bin/activate

python -m pip install --upgrade pip
python -m pip install -e ".[build]"

python -m PyInstaller --clean --noconfirm ArchiveVoice.spec

echo "Built dist/Archive Voice.app"

