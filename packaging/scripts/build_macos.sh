#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

if [[ ! -x ".venv/bin/python" ]]; then
  python3 -m venv .venv
fi

VERSION="$(.venv/bin/python - <<'PY'
import pathlib
import re

text = pathlib.Path("pyproject.toml").read_text()
print(re.search(r'^version = "([^"]+)"', text, re.MULTILINE).group(1))
PY
)"
ARCH="$(uname -m)"
if [[ "$ARCH" == "x86_64" ]]; then
  DIST_ARCH="mac-x64"
else
  DIST_ARCH="mac-arm64"
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[build]"

mkdir -p .pyinstaller-cache
PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache" .venv/bin/python -m PyInstaller --clean --noconfirm ArchiveVoice.spec

echo "Built dist/Archive Voice.app"

rm -rf build
rm -rf dist/dmg-stage
mkdir -p dist/dmg-stage
cp -cR "dist/Archive Voice.app" dist/dmg-stage/ 2>/dev/null || cp -R "dist/Archive Voice.app" dist/dmg-stage/
ln -s /Applications dist/dmg-stage/Applications
hdiutil create \
  -volname "Archive Voice $VERSION" \
  -srcfolder dist/dmg-stage \
  -ov \
  -format UDZO \
  "dist/ArchiveVoice-$VERSION-$DIST_ARCH.dmg"

echo "Built dist/ArchiveVoice-$VERSION-$DIST_ARCH.dmg"
