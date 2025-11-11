#!/bin/bash

# AASSH Installer
# A more robust installation script for various Linux distributions.

set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
SCRIPT_NAME="aassh"
SOURCE_URL="https://raw.githubusercontent.com/C0dWiz/aassh/main/aassh.py"
PYTHON_DEPS="pyyaml rich"
MIN_PYTHON_VERSION="3.7"

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

check_python_version() {
    local python_cmd="python3"
    if ! command -v "$python_cmd" &> /dev/null; then
        error "Python 3 is required but not found. Please install Python 3.7 or higher."
    fi

    local version
    version=$("$python_cmd" -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    
    if [ "$(echo "$version" | awk -F. '{print $1$2}')" -lt "37" ]; then
        error "Python 3.7 or higher is required. Found version $version."
    fi
    
    info "Found Python $version"
}

check_dependencies() {
    info "Checking dependencies..."
    
    check_python_version

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
}

install_python_deps() {
    info "Installing Python dependencies ($PYTHON_DEPS)..."
    
    # Try different installation methods
    if pip3 install --user $PYTHON_DEPS; then
        success "Dependencies installed successfully"
    else
        warn "Standard pip install failed. Trying with --break-system-packages..."
        if pip3 install --user --break-system-packages $PYTHON_DEPS; then
            success "Dependencies installed with --break-system-packages"
        else
            warn "Failed to install with --break-system-packages. Trying system-wide install..."
            if pip3 install $PYTHON_DEPS; then
                success "Dependencies installed system-wide"
            else
                error "Failed to install Python dependencies. Please install manually: pip3 install $PYTHON_DEPS"
            fi
        fi
    fi
}

download_script() {
    local temp_dir="$1"
    info "Downloading aassh script from GitHub..."
    
    if ! $DOWNLOADER "$SOURCE_URL" > "$temp_dir/$SCRIPT_NAME"; then
        error "Failed to download aassh script. Please check your internet connection."
    fi
    
    if [ ! -s "$temp_dir/$SCRIPT_NAME" ]; then
        error "Downloaded file is empty. Please try again."
    fi
}

install_script() {
    local temp_dir="$1"
    info "Installing the aassh script to $INSTALL_DIR..."
    
    mkdir -p "$INSTALL_DIR"
    INSTALL_PATH="$INSTALL_DIR/$SCRIPT_NAME"
    
    if ! mv "$temp_dir/$SCRIPT_NAME" "$INSTALL_PATH"; then
        error "Failed to move script to installation directory."
    fi
    
    if ! chmod +x "$INSTALL_PATH"; then
        error "Failed to make script executable."
    fi
    
    success "Script installed to $INSTALL_PATH"
}

create_sample_config() {
    local install_path="$1"
    CONFIG_DIR="${HOME}/.aassh"
    CONFIG_FILE="${CONFIG_DIR}/config.yml"
    
    if [ ! -f "$CONFIG_FILE" ]; then
        info "Creating a sample configuration file..."
        if ! "$install_path" --create-sample-config; then
            warn "Failed to create sample configuration. You can create it manually later."
        fi
    else
        info "Configuration file already exists at $CONFIG_FILE"
    fi
}

check_path() {
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        warn "Your PATH does not seem to include $INSTALL_DIR."
        warn "Please add the following line to your shell profile (e.g., ~/.bashrc, ~/.zshrc):"
        echo -e "\n  \033[1mexport PATH=\"\$PATH:$INSTALL_DIR\"\033[0m\n"
        
        # Detect shell and suggest specific file
        local shell_rc
        case "$SHELL" in
            */bash) shell_rc="~/.bashrc" ;;
            */zsh) shell_rc="~/.zshrc" ;;
            *) shell_rc="your shell configuration file" ;;
        esac
        
        warn "Then run: source $shell_rc"
    fi
}

main() {
    echo -e "\033[1;36m"
    echo "╔══════════════════════════════════════╗"
    echo "║          AASSH Installer            ║"
    echo "║    SSH Connection Manager v1.1.0    ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "\033[0m"
    
    check_dependencies
    
    TMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TMP_DIR"' EXIT
    
    download_script "$TMP_DIR"
    install_python_deps
    install_script "$TMP_DIR"
    create_sample_config "$INSTALL_DIR/$SCRIPT_NAME"
    check_path
    
    success "Installation complete!"
    echo -e "\nRun '\033[1maassh\033[0m' to get started."
    echo "Edit your profiles at: ~/.aassh/config.yml"
    echo -e "\nFor Mosh support, install mosh package:"
    echo "  Ubuntu/Debian: sudo apt install mosh"
    echo "  macOS: brew install mosh"
}

main "$@"