#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[build]"

mkdir -p .pyinstaller-cache
PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache" .venv/bin/python -m PyInstaller --clean --noconfirm ArchiveVoice.spec

echo "Built dist/Archive Voice.app"

rm -rf dist/dmg-stage
mkdir -p dist/dmg-stage
cp -R "dist/Archive Voice.app" dist/dmg-stage/
ln -s /Applications dist/dmg-stage/Applications
hdiutil create \
  -volname "Archive Voice 0.2.0" \
  -srcfolder dist/dmg-stage \
  -ov \
  -format UDZO \
  "dist/ArchiveVoice-0.2.0-mac-arm64.dmg"

echo "Built dist/ArchiveVoice-0.2.0-mac-arm64.dmg"
