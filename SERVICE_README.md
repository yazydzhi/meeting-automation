# 🚀 Сервис автоматизации встреч

Полноценный системный сервис для автоматизации встреч, работающий в фоновом режиме с мониторингом и логированием.

## ✨ Возможности

- **🔄 Автоматическая работа** - запуск при загрузке системы
- **⏰ Планировщик задач** - настраиваемые интервалы проверки
- **📊 Мониторинг** - отслеживание состояния и производительности
- **📋 Логирование** - детальные логи всех операций
- **📱 Умные уведомления** - только при наличии изменений
- **🖥️ Кроссплатформенность** - поддержка macOS и Linux

## 🏗️ Архитектура

```
src/
├── service_manager.py          # Основной сервис
├── media_processor.py          # Обработка медиа
├── drive_sync.py              # Синхронизация Drive
└── notion_templates.py        # Шаблоны Notion

scripts/
├── install_service.sh         # Установка сервиса
├── service_control.sh         # Управление сервисом
└── monitor_service.py         # Мониторинг

systemd/                        # Linux systemd
launchd/                        # macOS launchd
```

## 🚀 Установка

### 1. Подготовка

Убедитесь, что проект настроен и работает:

```bash
# Активируйте виртуальное окружение
source venv/bin/activate

# Проверьте работу основного скрипта
python meeting_automation_personal_only.py --help
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Установка сервиса

```bash
# Сделайте скрипты исполняемыми
chmod +x scripts/*.sh

# Установите сервис
./scripts/install_service.sh
```

## 🔧 Управление сервисом

### macOS (launchd)

```bash
# Запуск
launchctl start com.yazydzhi.meeting-automation

# Остановка
launchctl stop com.yazydzhi.meeting-automation

# Статус
launchctl list | grep meeting-automation

# Логи
tail -f logs/service.log
```

### Linux (systemd)

```bash
# Запуск
sudo systemctl start meeting-automation

# Остановка
sudo systemctl stop meeting-automation

# Статус
sudo systemctl status meeting-automation

# Логи
sudo journalctl -u meeting-automation -f
```

### Универсальные скрипты

```bash
# Управление сервисом
./scripts/service_control.sh start
./scripts/service_control.sh stop
./scripts/service_control.sh restart
./scripts/service_control.sh status
./scripts/service_control.sh logs
./scripts/service_control.sh follow-logs

# Мониторинг
python scripts/monitor_service.py
python scripts/monitor_service.py --continuous --interval 30
python scripts/monitor_service.py --save
```

## ⚙️ Конфигурация

### Переменные окружения

Создайте файл `.env` с необходимыми настройками:

```bash
# Google API
GOOGLE_CREDENTIALS=creds/client_secret.json
PERSONAL_CALENDAR_ID=your_calendar_id
PERSONAL_DRIVE_PARENT_ID=your_drive_folder_id

# Notion
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Медиа обработка
MEDIA_OUTPUT_FORMAT=mp3
MEDIA_QUALITY=medium
MEDIA_SYNC_ROOT=data/synced
MEDIA_CLEANUP_DAYS=30

# Временная зона
TIMEZONE=Europe/Moscow
```

### Настройка интервалов

При запуске сервиса можно настроить интервалы:

```bash
# Проверка каждые 5 минут, медиа каждые 30 минут
python src/service_manager.py --interval 300 --media-interval 1800

# Быстрая проверка для тестирования
python src/service_manager.py --interval 60 --media-interval 300
```

## 📊 Мониторинг

### Автоматический мониторинг

```bash
# Непрерывный мониторинг каждые 30 секунд
python scripts/monitor_service.py --continuous --interval 30

# Сохранение отчетов в файлы
python scripts/monitor_service.py --continuous --save
```

### Проверка состояния

```bash
# Статус сервиса
./scripts/service_control.sh status

# Последние логи
./scripts/service_control.sh logs

# Отслеживание логов в реальном времени
./scripts/service_control.sh follow-logs
```

## 🔍 Логи и отладка

### Структура логов

```
logs/
├── service_YYYYMMDD.log       # Основные логи сервиса
├── service.log                # Стандартный вывод (macOS)
├── service_error.log          # Стандартные ошибки (macOS)
└── monitor_report_*.txt       # Отчеты мониторинга
```

### Уровни логирования

- **INFO** - обычные операции
- **WARNING** - предупреждения
- **ERROR** - ошибки
- **❌** - критические ошибки
- **✅** - успешные операции
- **⚠️** - предупреждения

### Отладка

```bash
# Запуск в режиме отладки
python src/service_manager.py --interval 60

# Проверка логов в реальном времени
tail -f logs/service_*.log

# Анализ ошибок
grep "ERROR\|❌" logs/service_*.log
```

## 🚨 Устранение неполадок

### Сервис не запускается

1. **Проверьте права доступа:**
   ```bash
   chmod +x scripts/*.sh
   chmod +x src/service_manager.py
   ```

2. **Проверьте виртуальное окружение:**
   ```bash
   source venv/bin/activate
   python -c "import src.service_manager"
   ```

3. **Проверьте переменные окружения:**
   ```bash
   python -c "from meeting_automation_personal_only import load_env_or_fail; print(load_env_or_fail())"
   ```

### Ошибки Google API

1. **Проверьте токены:**
   ```bash
   ls -la tokens/
   ls -la creds/
   ```

2. **Обновите токены:**
   ```bash
   python init_project.py prepare
   ```

### Проблемы с логированием

1. **Создайте директорию логов:**
   ```bash
   mkdir -p logs
   chmod 755 logs
   ```

2. **Проверьте права записи:**
   ```bash
   touch logs/test.log
   rm logs/test.log
   ```

## 🔄 Обновление сервиса

```bash
# Остановите сервис
./scripts/service_control.sh stop

# Обновите код
git pull origin main

# Перезапустите сервис
./scripts/service_control.sh start
```

## 📱 Уведомления

Сервис отправляет уведомления в Telegram только при наличии изменений:

- **Новые встречи** в календаре
- **Обработанные медиа файлы**
- **Очищенные старые файлы**
- **Ошибки и предупреждения**

## 🎯 Производительность

### Рекомендуемые настройки

- **Интервал проверки**: 300 секунд (5 минут)
- **Интервал медиа**: 1800 секунд (30 минут)
- **Очистка логов**: каждые 7 дней
- **Максимум папок**: 5-10 для медиа обработки

### Мониторинг ресурсов

```bash
# Использование CPU и RAM
python scripts/monitor_service.py --continuous --interval 60

# Детальная информация о процессах
ps aux | grep service_manager.py
```

## 🔒 Безопасность

- **Изолированное выполнение** в виртуальном окружении
- **Ограниченные права доступа** к файловой системе
- **Безопасное хранение** токенов в .env файле
- **Логирование** всех операций для аудита

## 📚 Дополнительные ресурсы

- [Основной README](README.md) - описание проекта
- [Отчет о медиа обработке](MEDIA_PROCESSING_IMPLEMENTATION_REPORT.md)
- [Отчет об умных уведомлениях](SMART_NOTIFICATIONS_IMPLEMENTATION_REPORT.md)
- [Системные требования](PRODUCTION_SYSTEM_STATUS_REPORT.md)

## 🆘 Поддержка

При возникновении проблем:

1. **Проверьте логи:** `./scripts/service_control.sh logs`
2. **Запустите мониторинг:** `python scripts/monitor_service.py`
3. **Проверьте статус:** `./scripts/service_control.sh status`
4. **Перезапустите сервис:** `./scripts/service_control.sh restart`

---

**🎯 Сервис готов к полноценному использованию в продакшн среде!**
