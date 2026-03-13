#!/bin/bash

# AASSH Installer
# Isolated install with virtualenv and optional uninstall.

set -euo pipefail

INSTALL_DIR="${HOME}/.local/bin"
APP_DIR="${HOME}/.local/share/aassh"
VENV_DIR="${APP_DIR}/venv"
APP_SCRIPT="${APP_DIR}/aassh.py"
SCRIPT_NAME="aassh"
INSTALL_PATH="${INSTALL_DIR}/${SCRIPT_NAME}"
SOURCE_URL="https://raw.githubusercontent.com/C0dwiz/aassh/refs/heads/dev/aassh.py"
PYTHON_DEPS=(pyyaml rich ruamel.yaml)
MIN_PYTHON_VERSION="3.8"
EXPECTED_SHA256="${AASSH_SHA256:-}"

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
        error "Python 3 is required but not found. Please install Python 3.8 or higher."
    fi

    local version
    version=$("$python_cmd" -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")

    if [[ "$(printf '%s\n' "$MIN_PYTHON_VERSION" "$version" | sort -V | head -n1)" != "$MIN_PYTHON_VERSION" ]]; then
        error "Python 3.8 or higher is required. Found version $version."
    fi

    info "Found Python $version"
}

check_dependencies() {
    info "Checking dependencies..."

    check_python_version

    if ! python3 -m venv --help &> /dev/null; then
        error "python3-venv is required but not found. Please install python3-venv package."
    fi

    if command -v curl &> /dev/null; then
        DOWNLOADER="curl -fsSL"
    elif command -v wget &> /dev/null; then
        DOWNLOADER="wget -qO-"
    else
        error "You need either 'curl' or 'wget' to download the script."
    fi
}

create_virtualenv() {
    info "Creating isolated Python environment in ${VENV_DIR}..."
    mkdir -p "$APP_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/python" -m pip install --upgrade pip
}

install_python_deps() {
    info "Installing Python dependencies (${PYTHON_DEPS[*]}) into virtualenv..."
    "$VENV_DIR/bin/python" -m pip install "${PYTHON_DEPS[@]}"
    success "Dependencies installed successfully"
}

verify_checksum_if_available() {
    local file_path="$1"
    if [[ -z "$EXPECTED_SHA256" ]]; then
        warn "SHA256 checksum is not set (AASSH_SHA256). Skipping checksum verification."
        return 0
    fi

    if ! command -v sha256sum &> /dev/null; then
        error "sha256sum not found but AASSH_SHA256 is set. Install coreutils or unset AASSH_SHA256."
    fi

    if ! echo "$EXPECTED_SHA256  $file_path" | sha256sum -c -; then
        error "Checksum verification failed for downloaded script."
    fi

    success "Checksum verification passed"
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

    verify_checksum_if_available "$temp_dir/$SCRIPT_NAME"
}

install_script() {
    local temp_dir="$1"
    info "Installing the aassh script to $APP_DIR and launcher to $INSTALL_DIR..."

    mkdir -p "$APP_DIR"
    mkdir -p "$INSTALL_DIR"

    if ! mv "$temp_dir/$SCRIPT_NAME" "$APP_SCRIPT"; then
        error "Failed to move script to application directory."
    fi

    if ! chmod +x "$APP_SCRIPT"; then
        error "Failed to make application script executable."
    fi

    cat > "$INSTALL_PATH" <<EOF
#!/bin/bash
exec "${VENV_DIR}/bin/python" "${APP_SCRIPT}" "\$@"
EOF

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

detect_shell_rc() {
    case "$SHELL" in
        */bash) echo "$HOME/.bashrc" ;;
        */zsh) echo "$HOME/.zshrc" ;;
        */fish) echo "$HOME/.config/fish/config.fish" ;;
        *) echo "" ;;
    esac
}

append_path_if_confirmed() {
    local shell_rc="$1"
    if [[ -z "$shell_rc" ]]; then
        warn "Could not detect shell config file automatically."
        return
    fi

    local export_line="export PATH=\"\$PATH:${INSTALL_DIR}\""
    if [[ -f "$shell_rc" ]] && grep -Fq "$INSTALL_DIR" "$shell_rc"; then
        info "PATH already configured in $shell_rc"
        return
    fi

    read -r -p "Add $INSTALL_DIR to PATH in $shell_rc? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        echo "$export_line" >> "$shell_rc"
        success "Added PATH export to $shell_rc"
        warn "Run: source $shell_rc"
    fi
}

check_path() {
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        warn "Your PATH does not seem to include $INSTALL_DIR."
        warn "Please add the following line to your shell profile (e.g., ~/.bashrc, ~/.zshrc):"
        echo -e "\n  \033[1mexport PATH=\"\$PATH:$INSTALL_DIR\"\033[0m\n"

        local shell_rc
        shell_rc=$(detect_shell_rc)
        if [[ -n "$shell_rc" ]]; then
            warn "Then run: source $shell_rc"
            append_path_if_confirmed "$shell_rc"
        fi
    fi
}

uninstall() {
    info "Uninstalling AASSH..."

    if [[ -f "$INSTALL_PATH" ]]; then
        rm -f "$INSTALL_PATH"
        success "Removed launcher: $INSTALL_PATH"
    fi

    if [[ -d "$APP_DIR" ]]; then
        rm -rf "$APP_DIR"
        success "Removed application directory: $APP_DIR"
    fi

    read -r -p "Remove ~/.aassh/config.yml as well? [y/N] " answer
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.aassh"
        success "Removed ~/.aassh configuration"
    fi

    success "Uninstall complete"
}

main() {
    if [[ "${1:-}" == "--uninstall" ]]; then
        uninstall
        return
    fi

    echo -e "\033[1;36m"
    echo "╔══════════════════════════════════════╗"
    echo "║          AASSH Installer            ║"
    echo "║    SSH Connection Manager v1.2.0    ║"
    echo "╚══════════════════════════════════════╝"
    echo -e "\033[0m"

    check_dependencies

    TMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TMP_DIR"' EXIT

    download_script "$TMP_DIR"
    create_virtualenv
    install_python_deps
    install_script "$TMP_DIR"
    create_sample_config "$INSTALL_PATH"
    check_path

    success "Installation complete!"
    echo -e "\nRun '\033[1maassh\033[0m' to get started."
    echo "Edit your profiles at: ~/.aassh/config.yml"
    echo -e "\nFor Mosh support, install mosh package:"
    echo "  Ubuntu/Debian: sudo apt install mosh"
    echo "  macOS: brew install mosh"
}

main "$@"