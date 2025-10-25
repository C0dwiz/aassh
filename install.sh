#!/bin/bash

# AASSH Installer
# A more robust installation script for various Linux distributions.

set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_NAME="aassh"
SOURCE_URL="https://raw.githubusercontent.com/C0dWiz/aassh/main/aassh.py"
PYTHON_DEPS="pyyaml rich"

info() {
    echo -e "\033[1;34m[INFO]\033[0m $1"
}

warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1" >&2
    exit 1
}

success() {
    echo -e "\033[1;32m[SUCCESS]\033[0m $1"
}


info "Checking dependencies..."

if ! command -v python3 &> /dev/null; then
    error "Python 3 is required but not found. Please install it first."
fi

if ! command -v pip3 &> /dev/null; then
    error "pip3 is required but not found. Please install python3-pip package."
fi

if command -v curl &> /dev/null; then
    DOWNLOADER="curl -fsSL"
elif command -v wget &> /dev/null; then
    DOWNLOADER="wget -qO-"
else
    error "You need either 'curl' or 'wget' to download the script."
fi


TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

info "Downloading aassh script from GitHub..."
$DOWNLOADER "$SOURCE_URL" > "$TMP_DIR/$SCRIPT_NAME"

info "Installing Python dependencies ($PYTHON_DEPS)..."
if ! pip3 install --user $PYTHON_DEPS; then
    warn "Standard pip install failed. This might be due to PEP 668 (externally-managed environments)."
    info "Attempting to install with --break-system-packages..."
    if ! pip3 install --user --break-system-packages $PYTHON_DEPS; then
        error "Failed to install Python dependencies even with workaround. \nPlease consider using 'pipx' or a virtual environment to install the dependencies manually."
    fi
fi

info "Installing the aassh script to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"

INSTALL_PATH="$INSTALL_DIR/$SCRIPT_NAME"
mv "$TMP_DIR/$SCRIPT_NAME" "$INSTALL_PATH"
chmod +x "$INSTALL_PATH"


CONFIG_DIR="${HOME}/.aassh"
CONFIG_FILE="${CONFIG_DIR}/config.yml"
if [ ! -f "$CONFIG_FILE" ]; then
    info "Creating a sample configuration file..."
    "$INSTALL_PATH" --create-sample-config
fi

if [[ ":$PATH:" != ":$INSTALL_DIR:"* ]]; then
    warn "Your PATH does not seem to include $INSTALL_DIR."
    warn "Please add the following line to your shell profile (e.g., ~/.bashrc, ~/.zshrc):"
    echo -e "\n  \033[1mexport PATH=\"$PATH:$INSTALL_DIR\"
\033[0m\n"
    warn "You will need to restart your shell or run 'source ~/.bashrc' for the changes to take effect."
fi

success "Installation complete!"
echo -e "\nRun '\033[1maassh\033[0m' to get started."
echo "You can edit your profiles at: $CONFIG_FILE"