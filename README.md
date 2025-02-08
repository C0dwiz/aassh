# aassh - Менеджер SSH подключений

aassh - это простой инструмент командной строки для управления и подключения к SSH серверам. Он позволяет сохранять параметры подключения (имя пользователя, IP-адрес, порт) и легко подключаться к серверам по имени. **ВНИМАНИЕ: aassh не поддерживает хранение паролей. Рекомендуется использовать SSH ключи для безопасной аутентификации.**

## Особенности

•   **Управление подключениями:** Добавляйте, редактируйте и удаляйте SSH подключения.
•   **Список подключений:** Выводите список всех сохраненных подключений.
•   **Подключение по имени:** Легко подключайтесь к серверам, используя их сохраненные имена.
•   **Простая установка:** Установите aassh одной командой.
•   **Безопасность:** Разработан для работы с SSH ключами.

## Установка

Используйте следующую команду для установки aassh:

```bash
sudo bash -c "$(curl -sL https://github.com/c0dwiz/aassh/raw/main/aassh.sh)" @ instal
# Эта команда скачает скрипт установки и запустит его с правами суперпользователя.
```

## Использование

После установки aassh станет доступным из любого места в терминале.

### Основные команды

•   aassh --help: Выводит справку по использованию aassh.
•   aassh --list: Выводит список всех сохраненных SSH подключений.
•   aassh --add: Добавляет новое SSH подключение (запрашивает параметры в интерактивном режиме).
•   aassh --connect <имя>: Подключается к SSH серверу с указанным именем.
•   aassh --edit <имя>: Редактирует существующее SSH подключение.
•   aassh --delete <имя>: Удаляет существующее SSH подключение.
•   aassh --version: Выводит информацию о версии aassh.

### Примеры

•   **Добавление нового подключения:**

```bash
    aassh --add
# Следуйте инструкциям на экране для ввода имени, пользователя, IP-адреса и порта
```
•   **Подключение к серверу:**

```bash
    aassh --connect my_server
```

•   **Редактирование существующего подключения:**

```bash
    aassh --edit my_server
```
•   **Удаление подключения:**

```bash
    aassh --delete my_server
```
### Использование SSH ключей

aassh разработан для работы с SSH ключами. **НАСТОЯТЕЛЬНО РЕКОМЕНДУЕТСЯ ИСПОЛЬЗОВАТЬ SSH КЛЮЧИ ВМЕСТО ПАРОЛЕЙ ДЛЯ БОЛЕЕ БЕЗОПАСНОЙ АУТЕНТИФИКАЦИИ.**

1.  **Создайте SSH ключ (если у вас его еще нет):**

```bash
    ssh-keygen -t rsa -b 4096
```
2.  **Скопируйте публичный ключ на удаленный сервер:**

```bash
    ssh-copy-id user@ip_address
```
После настройки SSH ключей aassh будет подключаться к серверам автоматически, без необходимости ввода пароля.

## Деинсталляция

Для удаления aassh используйте следующую команду:

```bash
aassh --uninstall
```

## Безопасность

•   **SSH Ключи:** Используйте SSH ключи для аутентификации. aassh не предназначен для хранения паролей.
•   **Конфигурационный файл:** Убедитесь, что файл ~/.config/aassh/config имеет права доступа 600 (только чтение и запись для владельца):
    
```bash
    chmod 600 ~/.config/aassh/config•   
```
**Доверие:**  Будьте осторожны при выполнении скриптов, скачанных из интернета. Просмотрите код скрипта перед выполнением.

## Лицензия

[MIT License](LICENSE)
