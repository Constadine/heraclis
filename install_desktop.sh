#!/usr/bin/env bash

# Installer for Home Workout Logger
# - Creates a wrapper in ~/.local/bin/hw
# - Creates a desktop entry in ~/.local/share/applications
# - Uses uv if available, otherwise falls back to python3

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="HeraCLIs"
APP_ID="heraclis"
WRAPPER_NAME="hw"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/${APP_ID}.desktop"

echo "Installing $APP_NAME launcher..."

# 1) Ensure directories
mkdir -p "$BIN_DIR" "$DESKTOP_DIR"

# 2) Create wrapper
WRAPPER_PATH="$BIN_DIR/$WRAPPER_NAME"
cat > "$WRAPPER_PATH" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_DIR="__PROJECT_DIR__"
cd "$PROJECT_DIR"
if command -v uv >/dev/null 2>&1; then
  exec uv run hw.py "$@"
else
  exec python3 hw.py "$@"
fi
SH

# Inject actual project path
sed -i "s#__PROJECT_DIR__#${PROJECT_DIR//\//\\/}#g" "$WRAPPER_PATH"
chmod +x "$WRAPPER_PATH"

# 3) Pick icon (optional)
ICON_PATH="utilities-terminal"  # fallback theme icon
if [ -f "$PROJECT_DIR/sounds/timer.png" ]; then
  ICON_PATH="$PROJECT_DIR/sounds/timer.png"
elif [ -f "$PROJECT_DIR/icon.png" ]; then
  ICON_PATH="$PROJECT_DIR/icon.png"
fi

# 4) Create desktop entry
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Type=Application
Name=$APP_NAME
Comment=Log your home workouts quickly
Exec=$WRAPPER_PATH
Terminal=true
Icon=$ICON_PATH
Categories=Utility;Fitness;
Keywords=workout;fitness;log;cli;
EOF

chmod +x "$DESKTOP_FILE"

# 5) Try to refresh the desktop database (optional)
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" || true
fi

echo
echo "✅ Installed launcher: $DESKTOP_FILE"
echo "➡  You can now search for '$APP_NAME' in your applications menu."
echo "➡  The command-line wrapper is installed at: $WRAPPER_PATH"
echo
echo "Tip: If the icon doesn't show immediately, log out/in or run:"
echo "  update-desktop-database $DESKTOP_DIR 2>/dev/null || true"
echo

