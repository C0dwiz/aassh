#!/bin/bash
APP_NAME="aassh"
VERSION="1.0.0"
CONFIG_DIR="$HOME/.config/$APP_NAME"
CONFIG_FILE="$CONFIG_DIR/config"
BIN_DIR="/usr/local/bin"
BIN_FILE="$BIN_DIR/$APP_NAME"

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
  echo
  echo "Конфигурационный файл: $CONFIG_FILE"
}

print_version() {
  echo "$APP_NAME v$VERSION"
}

create_config_dir() {
  [ ! -d "$CONFIG_DIR" ] && mkdir -p "$CONFIG_DIR"
}

check_config_file() {
  create_config_dir
  [ ! -f "$CONFIG_FILE" ] && touch "$CONFIG_FILE"
}

check_name_exists() {
  local name="$1"
  grep -q "^name=$name$" "$CONFIG_FILE"
}

add_connection() {
  check_config_file

  read -p "Введите имя подключения: " name
  [ -z "$name" ] && { echo "Имя подключения не может быть пустым."; return 1; }
  check_name_exists "$name" && { echo "Подключение с именем '$name' уже существует."; return 1; }

  read -p "Введите имя пользователя: " user
  [ -z "$user" ] && { echo "Имя пользователя не может быть пустым."; return 1; }

  read -p "Введите IP адрес: " ip
  [ -z "$ip" ] && { echo "IP адрес не может быть пустым."; return 1; }

  read -p "Введите порт (по умолчанию 22): " port
  [ -z "$port" ] && port=22
  [[ "$port" =~ ^[0-9]+$ ]] || { echo "Порт должен быть числом."; return 1; }

  echo "name=$name" >> "$CONFIG_FILE"
  echo "user=$user" >> "$CONFIG_FILE"
  echo "ip=$ip" >> "$CONFIG_FILE"
  echo "port=$port" >> "$CONFIG_FILE"

  echo "Подключение '$name' успешно добавлено."
  echo "Используйте SSH ключи для безопасной аутентификации."

  return 0
}

edit_connection() {
  check_config_file
  local name="$1"

  [ -z "$name" ] && { echo "Укажите имя подключения для редактирования."; return 1; }
  check_name_exists "$name" || { echo "Подключение с именем '$name' не найдено."; return 1; }

  local user=$(grep "^user=" "$CONFIG_FILE" | sed -n "/name=$name/s/^user=\(.*\)/\1/p" | head -n 1)
  local ip=$(grep "^ip=" "$CONFIG_FILE" | sed -n "/name=$name/s/^ip=\(.*\)/\1/p" | head -n 1)

  local port=$(grep "^port=" "$CONFIG_FILE" | sed -n "/name=$name/s/^port=\(.*\)/\1/p" | head -n 1)

  echo "Редактирование подключения '$name':"
  read -p "Новое имя пользователя (текущее: $user): " new_user
  [ -n "$new_user" ] && user="$new_user"

  read -p "Новый IP адрес (текущий: $ip): " new_ip
  [ -n "$new_ip" ] && ip="$new_ip"

  read -p "Новый порт (текущий: $port): " new_port
  [ -n "$new_port" ] && { port="$new_port"; [[ "$port" =~ ^[0-9]+$ ]] || { echo "Порт должен быть числом."; return 1; } }

  sed -i "" "/name=$name/d" "$CONFIG_FILE"
  sed -i "" "/user=$name/d" "$CONFIG_FILE"
  sed -i "" "/ip=$name/d" "$CONFIG_FILE"
  sed -i "" "/port=$name/d" "$CONFIG_FILE"

  echo "name=$name" >> "$CONFIG_FILE"
  echo "user=$user" >> "$CONFIG_FILE"
  echo "ip=$ip" >> "$CONFIG_FILE"
  echo "port=$port" >> "$CONFIG_FILE"

  echo "Подключение '$name' успешно отредактировано."
}

delete_connection() {
  check_config_file
  local name="$1"

  [ -z "$name" ] && { echo "Укажите имя подключения для удаления."; return 1; }
  check_name_exists "$name" || { echo "Подключение с именем '$name' не найдено."; return 1; }

  read -p "Вы уверены, что хотите удалить подключение '$name'? (y/n): " confirm
  [[ "$confirm" != "y" && "$confirm" != "Y" ]] && { echo "Удаление отменено."; return 0; }

  sed -i "" "/name=$name/d" "$CONFIG_FILE"
  sed -i "" "/user=$name/d" "$CONFIG_FILE"
  sed -i "" "/ip=$name/d" "$CONFIG_FILE"
  sed -i "" "/port=$name/d" "$CONFIG_FILE"

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

  [ "$count" -eq 0 ] && echo "Нет сохраненных подключений."
}

connect_to_server() {
  check_config_file
  local name="$1"

  [ -z "$name" ] && { echo "Укажите имя подключения для подключения."; return 1; }
  check_name_exists "$name" || { echo "Подключение с именем '$name' не найдено."; return 1; }

  local user=$(grep "^user=" "$CONFIG_FILE" | sed -n "/name=$name/s/^user=\(.*\)/\1/p" | head -n 1)
  local ip=$(grep "^ip=" "$CONFIG_FILE" | sed -n "/name=$name/s/^ip=\(.*\)/\1/p" | head -n 1)
  local port=$(grep "^port=" "$CONFIG_FILE" | sed -n "/name=$name/s/^port=\(.*\)/\1/p" | head -n 1)

  [ -z "$user" ] || [ -z "$ip" ] || [ -z "$port" ] && { echo "Не удалось получить параметры подключения для '$name'."; return 1; }

  echo "Подключение к $user@$ip:$port..."
  ssh -p "$port" "$user@$ip"
}

install() {
  [ ! -d "$BIN_DIR" ] && sudo mkdir -p "$BIN_DIR"
  if [ ! -f "$BIN_FILE" ]; then
    sudo cp "$0" "$BIN_FILE"
    sudo chmod +x "$BIN_FILE"
    echo "$APP_NAME успешно установлен в $BIN_DIR"
  else
    echo "$APP_NAME уже установлен."
  fi
}

uninstall() {
  if [ -f "$BIN_FILE" ]; then
    sudo rm "$BIN_FILE"
    echo "$APP_NAME успешно удален."
  else
    echo "$APP_NAME не установлен."
  fi
}

if [ "$1" == "@" ] && [ "$2" == "install" ]; then
  shift
  shift
  install
  exit 0
fi

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

exit 