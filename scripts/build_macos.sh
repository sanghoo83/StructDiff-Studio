#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

# StructDiff Studio macOS build.
# Uses the system diff command at runtime when available.

python -m PyInstaller \
  --onefile \
  --windowed \
  --name StructDiffStudio \
  --add-data "assets/code_by_noah_logo.png:assets" \
  src/structdiff_studio.py

echo "Build complete. Check dist/StructDiffStudio."
