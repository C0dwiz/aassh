#!/bin/bash

APP_NAME="aassh"
VERSION="1.0.2"
CONFIG_DIR="$HOME/.config/$APP_NAME"
CONFIG_FILE="$CONFIG_DIR/config"
BIN_DIR="/usr/local/bin"
BIN_FILE="$BIN_DIR/$APP_NAME"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

detect_distro() {
  if command -v apt-get &> /dev/null; then
    echo "debian"
  elif command -v pacman &> /dev/null; then
    echo "arch"
  elif command -v yum &> /dev/null; then
    echo "redhat"
  elif command -v dnf &> /dev/null; then
    echo "fedora"
  elif command -v zypper &> /dev/null; then
    echo "suse"
  else
    echo "unknown"
  fi
}

print_help() {
  echo -e "${BLUE}Использование: ${APP_NAME} [опции]${NC}"
  echo
  echo -e "${YELLOW}Опции:${NC}"
  echo "  --list            Вывести список сохраненных подключений"
  echo "  --connect <имя>   Подключиться к сохраненному подключению"
  echo "  --add             Добавить новое подключение (интерактивный режим)"
  echo "  --edit <имя>      Редактировать существующее подключение"
  echo "  --delete <имя>    Удалить существующее подключение"
  echo "  --help            Вывести это сообщение"
  echo "  --version         Вывести версию программы"
  echo "  --install         Установить программу"
  echo "  --uninstall       Удалить программу"
  echo
  echo -e "${YELLOW}Конфигурационный файл: ${NC}${CONFIG_FILE}"
}

print_version() {
  echo -e "${GREEN}${APP_NAME} v${VERSION}${NC}"
}

create_config_dir() {
  mkdir -p "$CONFIG_DIR"
}

check_config_file() {
  create_config_dir
  touch "$CONFIG_FILE"
}

check_name_exists() {
  local name="$1"
  grep -q "^name=${name}$" "$CONFIG_FILE"
}

add_connection() {
  check_config_file

  read -r -p "Введите имя подключения: " name
  if [ -z "$name" ]; then
    echo -e "${RED}Имя подключения не может быть пустым.${NC}"
    return 1
  fi
  if check_name_exists "$name"; then
    echo -e "${RED}Подключение с именем '$name' уже существует.${NC}"
    return 1
  fi

  read -r -p "Введите имя пользователя: " user
  if [ -z "$user" ]; then
    echo -e "${RED}Имя пользователя не может быть пустым.${NC}"
    return 1
  fi

  read -r -p "Введите IP адрес: " ip
  if [ -z "$ip" ]; then
    echo -e "${RED}IP адрес не может быть пустым.${NC}"
    return 1
  fi

  read -r -p "Введите порт (по умолчанию 22): " port
  if [ -z "$port" ]; then
    port=22
  fi
  if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Порт должен быть числом.${NC}"
    return 1
  fi

  printf -v name_line "name=%s\n" "$name"
  printf -v user_line "user=%s\n" "$user"
  printf -v ip_line "ip=%s\n" "$ip"
  printf -v port_line "port=%s\n" "$port"

  echo "$name_line$user_line$ip_line$port_line" >> "$CONFIG_FILE"

  echo -e "${GREEN}Подключение '$name' успешно добавлено.${NC}"
  echo -e "${YELLOW}Используйте SSH ключи для безопасной аутентификации.${NC}"

  return 0
}


edit_connection() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo -e "${RED}Укажите имя подключения для редактирования.${NC}"
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo -e "${RED}Подключение с именем '$name' не найдено.${NC}"
    return 1
  fi

  local user=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^user=" | awk -F= '{print $2}')
  local ip=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^ip=" | awk -F= '{print $2}')
  local port=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^port=" | awk -F= '{print $2}')

  echo -e "${YELLOW}Редактирование подключения '$name':${NC}"
  read -r -p "Новое имя пользователя (текущее: $user): " new_user
  if [ -n "$new_user" ]; then
    user="$new_user"
  fi

  read -r -p "Новый IP адрес (текущий: $ip): " new_ip
  if [ -n "$new_ip" ]; then
    ip="$new_ip"
  fi

  read -r -p "Новый порт (текущий: $port): " new_port
  if [ -n "$new_port" ]; then
    port="$new_port"
    if ! [[ "$port" =~ ^[0-9]+$ ]]; then
      echo -e "${RED}Порт должен быть числом.${NC}"
      return 1
    fi
  fi

  printf -v name_line "name=%s\n" "$name"
  printf -v user_line "user=%s\n" "$user"
  printf -v ip_line "ip=%s\n" "$ip"
  printf -v port_line "port=%s\n" "$port"

  sed -i "/^name=$name$/,+3d" "$CONFIG_FILE"

  echo "$name_line$user_line$ip_line$port_line" >> "$CONFIG_FILE"

  echo -e "${GREEN}Подключение '$name' успешно отредактировано.${NC}"
}


delete_connection() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo -e "${RED}Укажите имя подключения для удаления.${NC}"
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo -e "${RED}Подключение с именем '$name' не найдено.${NC}"
    return 1
  fi

  read -r -p "Вы уверены, что хотите удалить подключение '$name'? (y/n): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Удаление отменено."
    return 0
  fi

  sed -i "/^name=$name$/,+3d" "$CONFIG_FILE"

  echo -e "${GREEN}Подключение '$name' успешно удалено.${NC}"
}


list_connections() {
  check_config_file

  local count=0
  echo -e "${YELLOW}Сохраненные подключения:${NC}"
  while IFS='=' read -r key value; do
    if [[ "$key" == "name" ]]; then
      echo "- $value"
      count=$((count + 1))
    fi
  done < "$CONFIG_FILE"

  if [ "$count" -eq 0 ]; then
    echo -e "${YELLOW}Нет сохраненных подключений.${NC}"
  fi
}

connect_to_server() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo -e "${RED}Укажите имя подключения для подключения.${NC}"
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo -e "${RED}Подключение с именем '$name' не найдено.${NC}"
    return 1
  fi

  local user=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^user=" | awk -F= '{print $2}')
  local ip=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^ip=" | awk -F= '{print $2}')
  local port=$(grep "^name=$name" "$CONFIG_FILE" -A 3 | grep "^port=" | awk -F= '{print $2}')


  if [ -z "$user" ] || [ -z "$ip" ] || [ -z "$port" ]; then
    echo -e "${RED}Не удалось получить параметры подключения для '$name'.${NC}"
    return 1
  fi

  echo -e "${BLUE}Подключение к $user@$ip:$port...${NC}"
  ssh -p "$port" "$user@$ip"
}

install() {
  local distro=$(detect_distro)

  if ! [ -d "$BIN_DIR" ]; then
    sudo mkdir -p "$BIN_DIR"
  fi

  if ! [ -f "$BIN_FILE" ]; then
    sudo cp "$0" "$BIN_FILE"
    sudo chmod +x "$BIN_FILE"

    if [[ "$distro" == "debian" ]] && command -v update-alternatives &> /dev/null; then
      sudo update-alternatives --install "$BIN_DIR/$APP_NAME" "$APP_NAME" "$BIN_FILE" 10
    fi

    echo -e "${GREEN}${APP_NAME} успешно установлен в ${BIN_DIR}${NC}"
  else
    echo -e "${YELLOW}${APP_NAME} уже установлен.${NC}"
  fi
}

uninstall() {
  local distro=$(detect_distro)

  if [ -f "$BIN_FILE" ]; then
    if [[ "$distro" == "debian" ]] && command -v update-alternatives &> /dev/null; then
      sudo update-alternatives --remove "$APP_NAME" "$BIN_FILE"
    fi

    sudo rm "$BIN_FILE"
    echo -e "${GREEN}${APP_NAME} успешно удален.${NC}"
  else
    echo -e "${YELLOW}${APP_NAME} не установлен.${NC}"
  fi
}

case "$1" in
  --list) list_connections ;;
  --connect) connect_to_server "$2" ;;
  --add) add_connection ;;
  --edit) edit_connection "$2" ;;
  --delete) delete_connection "$2" ;;
  --help) print_help ;;
  --version) print_version ;;
  --install) install ;;
  --uninstall) uninstall ;;
  *) print_help; exit 1 ;;
esac

exit 0