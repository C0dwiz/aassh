#!/bin/bash

APP_NAME="aassh"
VERSION="1.0.1"
CONFIG_DIR="$HOME/.config/$APP_NAME"
CONFIG_FILE="$CONFIG_DIR/config"
BIN_DIR="/usr/local/bin"
BIN_FILE="$BIN_DIR/$APP_NAME"

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
  echo "Использование: $APP_NAME [опции]"
  echo
  echo "Опции:"
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
  echo "Конфигурационный файл: $CONFIG_FILE"
}

print_version() {
  echo "$APP_NAME v$VERSION"
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
  grep -q "^name=$name$" "$CONFIG_FILE"
}

add_connection() {
  check_config_file

  read -r -p "Введите имя подключения: " name
  if [ -z "$name" ]; then
    echo "Имя подключения не может быть пустым."
    return 1
  fi
  if check_name_exists "$name"; then
    echo "Подключение с именем '$name' уже существует."
    return 1
  fi

  read -r -p "Введите имя пользователя: " user
  if [ -z "$user" ]; then
    echo "Имя пользователя не может быть пустым."
    return 1
  fi

  read -r -p "Введите IP адрес: " ip
  if [ -z "$ip" ]; then
    echo "IP адрес не может быть пустым."
    return 1
  fi

  read -r -p "Введите порт (по умолчанию 22): " port
  if [ -z "$port" ]; then
    port=22
  fi
  if ! [[ "$port" =~ ^[0-9]+$ ]]; then
    echo "Порт должен быть числом."
    return 1
  fi

  printf "name=%s\n" "$name" >> "$CONFIG_FILE"
  printf "user=%s\n" "$user" >> "$CONFIG_FILE"
  printf "ip=%s\n" "$ip" >> "$CONFIG_FILE"
  printf "port=%s\n" "$port" >> "$CONFIG_FILE"

  echo "Подключение '$name' успешно добавлено."

  echo "Используйте SSH ключи для безопасной аутентификации."

  return 0
}

edit_connection() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo "Укажите имя подключения для редактирования."
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo "Подключение с именем '$name' не найдено."
    return 1
  fi

  local user=$(grep "^user=" "$CONFIG_FILE" | grep "name=$name" | cut -d'=' -f2)
  local ip=$(grep "^ip=" "$CONFIG_FILE" | grep "name=$name" | cut -d'=' -f2)
  local port=$(grep "^port=" "$CONFIG_FILE" | grep "name=$name" | cut -d'=' -f2)

  echo "Редактирование подключения '$name':"
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
      echo "Порт должен быть числом."
      return 1
    fi
  fi

  temp_file=$(mktemp)
  trap "rm -f $temp_file" EXIT

  while IFS='=' read -r key value; do
    if [[ "$key" == "name" && "$value" == "$name" ]]; then
      continue
    elif [[ "$key" == "user" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    elif [[ "$key" == "ip" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    elif [[ "$key" == "port" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    fi
    printf "%s=%s\n" "$key" "$value" >> "$temp_file"
  done < "$CONFIG_FILE"

  printf "name=%s\n" "$name" >> "$temp_file"
  printf "user=%s\n" "$user" >> "$temp_file"
  printf "ip=%s\n" "$ip" >> "$temp_file"
  printf "port=%s\n" "$port" >> "$temp_file"

  mv "$temp_file" "$CONFIG_FILE"

  echo "Подключение '$name' успешно отредактировано."
}

delete_connection() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo "Укажите имя подключения для удаления."
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo "Подключение с именем '$name' не найдено."
    return 1
  fi

  read -r -p "Вы уверены, что хотите удалить подключение '$name'? (y/n): " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Удаление отменено."
    return 0
  fi

  temp_file=$(mktemp)
  trap "rm -f $temp_file" EXIT

  while IFS='=' read -r key value; do
    if [[ "$key" == "name" && "$value" == "$name" ]]; then
      continue
    elif [[ "$key" == "user" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    elif [[ "$key" == "ip" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    elif [[ "$key" == "port" && $(grep "name=$name" "$CONFIG_FILE") ]]; then
        continue
    fi
    printf "%s=%s\n" "$key" "$value" >> "$temp_file"
  done < "$CONFIG_FILE"

  mv "$temp_file" "$CONFIG_FILE"

  echo "Подключение '$name' успешно удалено."
}

list_connections() {
  check_config_file

  local count=0
  while IFS='=' read -r key value; do
    if [[ "$key" == "name" ]]; then
      echo "- $value"
      count=$((count + 1))
    fi
  done < "$CONFIG_FILE"

  if [ "$count" -eq 0 ]; then
    echo "Нет сохраненных подключений."
  fi
}

connect_to_server() {
  check_config_file
  local name="$1"

  if [ -z "$name" ]; then
    echo "Укажите имя подключения для подключения."
    return 1
  fi
  if ! check_name_exists "$name"; then
    echo "Подключение с именем '$name' не найдено."
    return 1
  fi

  local user=$(grep "^user=" "$CONFIG_FILE" | grep "name=$name" | cut -d'=' -f2)
  local ip=$(grep "^ip=" "$CONFIG_FILE" | grep "name=$name" | cut -d'=' -f2)
  local port=$(grep "^port=" "$CONFIG_FILE" | grep "name=$name" | cut -d

'=' -f2)

  if [ -z "$user" ] || [ -z "$ip" ] || [ -z "$port" ]; then
    echo "Не удалось получить параметры подключения для '$name'."
    return 1
  fi

  echo "Подключение к $user@$ip:$port..."
  ssh -p "$port" "$user@$ip"
}

install() {
  local distro=$(detect_distro)

  if [ ! -d "$BIN_DIR" ]; then
    sudo mkdir -p "$BIN_DIR"
  fi

  if [ ! -f "$BIN_FILE" ]; then
    sudo cp "$0" "$BIN_FILE"
    sudo chmod +x "$BIN_FILE"

    if [[ "$distro" == "debian" ]] && command -v update-alternatives &> /dev/null; then
      sudo update-alternatives --install "$BIN_DIR/$APP_NAME" "$APP_NAME" "$BIN_FILE" 10
    fi

    echo "$APP_NAME успешно установлен в $BIN_DIR"
  else
    echo "$APP_NAME уже установлен."
  fi
}

uninstall() {
  local distro=$(detect_distro)

  if [ -f "$BIN_FILE" ]; then
    if [[ "$distro" == "debian" ]] && command -v update-alternatives &> /dev/null; then
      sudo update-alternatives --remove "$APP_NAME" "$BIN_FILE"
    fi

    sudo rm "$BIN_FILE"
    echo "$APP_NAME успешно удален."
  else
    echo "$APP_NAME не установлен."
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
