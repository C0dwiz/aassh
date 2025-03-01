# aassh - SSH Connection Manager

<div align="center">

![aassh Logo](https://raw.githubusercontent.com/C0dwiz/aassh/main/docs/assets/logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.5-blue.svg)](https://github.com/C0dwiz/aassh/releases)
[![Shell Script](https://img.shields.io/badge/language-Shell-green.svg)](https://www.gnu.org/software/bash/)

*Простой и удобный менеджер SSH подключений для Linux*

</div>

## 📋 Описание

**aassh** - это легковесный инструмент командной строки для управления SSH подключениями. Программа позволяет сохранять, организовывать и быстро подключаться к вашим SSH серверам, используя удобные алиасы вместо запоминания IP-адресов и параметров.

## ✨ Особенности

- 🔐 **Безопасность**: Разработан для работы с SSH-ключами
- 📝 **Простое управление**: Интуитивный интерфейс командной строки
- 🚀 **Быстрое подключение**: Мгновенный доступ к серверам по имени
- 🔄 **Гибкая настройка**: Легкое редактирование параметров подключения
- 📦 **Простая установка**: Один скрипт для установки и настройки

## 🚀 Установка

### Автоматическая установка

```bash
curl -sSL https://raw.githubusercontent.com/C0dwiz/aassh/main/install.sh | bash
```

### Ручная установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/C0dwiz/aassh.git
```

2. Перейдите в директорию проекта:
```bash
cd aassh
```

3. Запустите установку:
```bash
./aassh.sh --install
```

## 🎯 Использование

### Основные команды

| Команда | Описание |
|---------|----------|
| `aassh --list` | Список всех сохраненных подключений |
| `aassh --add` | Добавить новое подключение |
| `aassh --connect <имя>` | Подключиться к серверу |
| `aassh --edit <имя>` | Редактировать существующее подключение |
| `aassh --delete <имя>` | Удалить подключение |
| `aassh --help` | Показать справку |
| `aassh --version` | Показать версию |

### Примеры использования

#### Добавление нового сервера
```bash
aassh --add
# Следуйте инструкциям для ввода:
# - Имени подключения
# - Имени пользователя
# - IP-адреса
# - Порта (по умолчанию 22)
```

#### Быстрое подключение
```bash
aassh --connect my_server
```

## 🔒 Настройка SSH-ключей

### 1. Создание нового ключа
```bash
ssh-keygen -t ed25519 -C "ваш@email.com"
```

### 2. Копирование ключа на сервер
```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
```

## ⚙️ Конфигурация

Конфигурационные файлы хранятся в:
- `~/.config/aassh/config` - основной конфигурационный файл
- `~/.ssh/config` - стандартный конфиг SSH (опционально)

### Права доступа
```bash
chmod 600 ~/.config/aassh/config
```

## 🗑️ Удаление

```bash
aassh --uninstall
```

## 🤝 Вклад в проект

1. Создайте форк проекта
2. Создайте ветку для ваших изменений (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте изменения в ваш форк (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## 📜 Лицензия

Распространяется под лицензией MIT. Смотрите файл [LICENSE](LICENSE) для получения дополнительной информации.

## 🔍 Устранение неполадок

### Общие проблемы

1. **Ошибка доступа к конфигурационному файлу**
   ```bash
   chmod 600 ~/.config/aassh/config
   ```

2. **Программа не найдена после установки**
   ```bash
   source ~/.bashrc
   ```

3. **Проблемы с SSH-ключами**
   ```bash
   ssh-add ~/.ssh/id_ed25519
   ```

## 📞 Поддержка

- 🐛 [Сообщить об ошибке](https://github.com/C0dwiz/aassh/issues)
- 💡 [Предложить улучшение](https://github.com/C0dwiz/aassh/issues)
- 📧 [Связаться с автором](https://github.com/C0dwiz)