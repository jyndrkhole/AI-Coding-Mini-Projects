#!/usr/bin/env bash
# Builds Reclaim Space.app — double-click to open the cleanup portal.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

APP_NAME="Reclaim Space"
APP_PATH="$ROOT/$APP_NAME.app"

rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

cat > "$APP_PATH/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>launcher</string>
  <key>CFBundleIdentifier</key>
  <string>com.reclaim.macos-space</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Reclaim Space</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.1.0</string>
  <key>CFBundleVersion</key>
  <string>1.1.0</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
PLIST

cat > "$APP_PATH/Contents/MacOS/launcher" <<LAUNCHER
#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$ROOT"
URL="http://127.0.0.1:8765"
cd "\$PROJECT_DIR"

alert() {
  osascript -e "display alert \"Reclaim Space\" message \"\$1\""
}

if ! command -v python3 >/dev/null 2>&1; then
  alert "Python 3 is required. Install it from python.org or Homebrew."
  exit 1
fi

if curl -sf "\$URL/api/disk" >/dev/null 2>&1; then
  open "\$URL"
  exit 0
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

exec python app.py
LAUNCHER

chmod +x "$APP_PATH/Contents/MacOS/launcher"

echo "Built $APP_PATH"
echo "Double-click '$APP_NAME.app' in Finder to launch."
