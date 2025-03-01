#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Константы
APP_NAME="aassh"
REPO_URL="https://github.com/C0dwiz/aassh"
SCRIPT_URL="https://raw.githubusercontent.com/C0dwiz/aassh/main/aassh.sh"
BIN_DIR="/usr/local/bin"
CONFIG_DIR="$HOME/.config/$APP_NAME"

check_requirements() {
    local missing_deps=()
    
    for cmd in curl wget ssh git; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${YELLOW}Отсутствуют необходимые зависимости: ${missing_deps[*]}${NC}"
        echo -e "Установите их с помощью вашего пакетного менеджера:"
        echo -e "Debian/Ubuntu: ${BLUE}sudo apt install ${missing_deps[*]}${NC}"
        echo -e "Fedora: ${BLUE}sudo dnf install ${missing_deps[*]}${NC}"
        echo -e "Arch Linux: ${BLUE}sudo pacman -S ${missing_deps[*]}${NC}"
        exit 1
    fi
}

get_sudo() {
    if [ "$(id -u)" -ne 0 ]; then
        if command -v sudo &> /dev/null; then
            echo "sudo"
        else
            echo -e "${RED}Для установки требуются права суперпользователя.${NC}"
            echo -e "${RED}Установите sudo или запустите скрипт от имени root.${NC}"
            exit 1
        fi
    fi
}

setup_directories() {
    local sudo_cmd=$(get_sudo)

    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"

    if [ ! -d "$BIN_DIR" ]; then
        $sudo_cmd mkdir -p "$BIN_DIR"
    fi
}

install_script() {
    local sudo_cmd=$(get_sudo)
    local temp_file="/tmp/$APP_NAME.sh"

    echo -e "${BLUE}Загрузка $APP_NAME...${NC}"

    if ! curl -sSL "$SCRIPT_URL" -o "$temp_file"; then
        echo -e "${RED}Ошибка загрузки скрипта.${NC}"
        exit 1
    fi

    $sudo_cmd mv "$temp_file" "$BIN_DIR/$APP_NAME"
    $sudo_cmd chmod +x "$BIN_DIR/$APP_NAME"

    if [ -x "$BIN_DIR/$APP_NAME" ]; then
        echo -e "${GREEN}$APP_NAME успешно установлен в $BIN_DIR${NC}"
    else
        echo -e "${RED}Ошибка установки $APP_NAME${NC}"
        exit 1
    fi
}

setup_environment() {
    if ! echo "$PATH" | grep -q "$BIN_DIR"; then
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.bashrc"
        echo "export PATH=\"\$PATH:$BIN_DIR\"" >> "$HOME/.zshrc" 2>/dev/null || true
    fi

    if [ ! -f "$CONFIG_DIR/config" ]; then
        touch "$CONFIG_DIR/config"
        chmod 600 "$CONFIG_DIR/config"
    fi
}

main() {
    echo -e "${BLUE}Начало установки $APP_NAME...${NC}"
    
    check_requirements
    setup_directories
    install_script
    setup_environment
    
    echo -e "${GREEN}Установка $APP_NAME завершена успешно!${NC}"
    echo -e "${YELLOW}Для применения изменений выполните:${NC}"
    echo -e "${BLUE}source ~/.bashrc${NC}"
    echo -e "\n${BLUE}Использование:${NC}"
    echo -e "  $APP_NAME --help    - показать справку"
    echo -e "  $APP_NAME --add     - добавить новое подключение"
    echo -e "  $APP_NAME --list    - показать список подключений"
}

main