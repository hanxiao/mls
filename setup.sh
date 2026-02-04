#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="ai.openclaw.qwen3-asr.plist"
PLIST_SRC="$PROJECT_DIR/$PLIST_NAME"
PLIST_DST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "Setting up Qwen3-ASR History..."
echo "Project directory: $PROJECT_DIR"

# Create venv if needed
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

# Install dependencies
echo "Installing dependencies..."
"$PROJECT_DIR/.venv/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

# Make scripts executable
chmod +x "$PROJECT_DIR/bin/server.py"
chmod +x "$PROJECT_DIR/bin/qwen3-asr"

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Generate launchd plist
cat > "$PLIST_SRC" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.openclaw.qwen3-asr</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PROJECT_DIR/.venv/bin/python</string>
        <string>$PROJECT_DIR/bin/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>HOME</key>
        <string>$HOME</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/server.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/server.log</string>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
EOF

# Unload existing service if running
if launchctl list | grep -q "ai.openclaw.qwen3-asr"; then
    echo "Stopping existing service..."
    launchctl unload "$PLIST_DST" 2>/dev/null || true
fi

# Install plist
echo "Installing launchd service..."
cp "$PLIST_SRC" "$PLIST_DST"
launchctl load "$PLIST_DST"

# Symlink wrapper to ~/.local/bin
mkdir -p "$HOME/.local/bin"
ln -sf "$PROJECT_DIR/bin/qwen3-asr" "$HOME/.local/bin/qwen3-asr"

echo ""
echo "Setup complete!"
echo "  - Server: http://127.0.0.1:18321"
echo "  - History UI: http://127.0.0.1:18321/history"
echo "  - Logs: $PROJECT_DIR/logs/server.log"
echo "  - CLI: qwen3-asr <audio_file> [language]"
