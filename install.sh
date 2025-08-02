#!/bin/bash
# AASSH-PY Installer
set -e

if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Aborting."
    exit 1
fi

TMP_DIR=$(mktemp -d)
trap "rm -rf $TMP_DIR" EXIT

echo "📥 Downloading aassh..."
curl -sSL https://raw.githubusercontent.com/C0dWiz/aassh/dev/aassh.py -o "$TMP_DIR/aassh.py"

echo "🔧 Installing Python dependencies..."
pip3 install --user pyyaml rich --break-system-packages

INSTALL_DIR="${HOME}/.local/bin"
mkdir -p "$INSTALL_DIR"
mv "$TMP_DIR/aassh.py" "$INSTALL_DIR/aassh"
chmod +x "$INSTALL_DIR/aassh"

CONFIG_DIR="${HOME}/.aassh"
CONFIG_FILE="${CONFIG_DIR}/config.yml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "📝 Creating sample configuration..."
    mkdir -p "$CONFIG_DIR"
    "$INSTALL_DIR/aassh" --create-sample-config
fi

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo "⚠️ Note: Please add the following to your shell configuration:"
    echo "  export PATH=\"\$PATH:${INSTALL_DIR}\""
fi

echo "✅ [bold]Installation complete![/bold]"
echo "Usage:"
echo "  aassh              # Interactive mode"
echo "  aassh -l           # List profiles"
echo "  aassh profile_name # Connect to specific profile"
echo "Edit your SSH profiles at: ${CONFIG_FILE}"
