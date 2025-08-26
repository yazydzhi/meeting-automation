# 🚀 Meeting Automation System

Система автоматизации встреч с поддержкой личного и рабочего аккаунтов через единую конфигурацию.

## ✨ Основные возможности

- **📅 Автоматическая обработка календарей** (iCal, Google Calendar API)
- **💾 Синхронизация с Google Drive** (API и локальные папки)
- **📝 Интеграция с Notion** для заметок о встречах
- **🎬 Обработка медиа файлов** (сжатие видео, извлечение аудио)
- **🎤 Транскрипция аудио** (Whisper, OpenAI API)
- **🤖 Анализ транскрипций** через OpenAI GPT
- **📱 Уведомления в Telegram**
- **⚙️ Единая конфигурация** для всех аккаунтов

## 🏗️ Архитектура

```
meeting_automation/
├── .env                          # Единая конфигурация
├── meeting_automation_universal.py  # Универсальный скрипт
├── src/
│   ├── config_manager.py         # Менеджер конфигурации
│   ├── service_manager.py        # Системный сервис
│   ├── calendar_handler.py       # Обработчик календарей
│   ├── media_processor.py        # Обработчик медиа файлов
│   ├── transcription_handler.py  # Обработчик транскрипций и саммари
│   ├── telegram_api.py           # API для Telegram
│   └── transcript_analyzer.py    # Анализатор транскрипций
├── scripts/
│   ├── monitor_service.py        # Мониторинг сервиса
│   └── folder_status_monitor.py  # Мониторинг папок встреч
├── data/                         # Данные кэша и статистики
│   ├── service_cache.json        # Кэш обработанных файлов
│   └── performance_stats.json    # Статистика производительности
└── logs/                         # Логи системы
```

## ⚙️ Конфигурация

### Основные параметры

```bash
# ========================================
# ОБЩИЕ НАСТРОЙКИ TELEGRAM И NOTION
# ========================================

# Telegram для уведомлений и отчетов
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Notion для заметок о встречах
NOTION_TOKEN=your_notion_api_token_here
NOTION_DATABASE_ID=your_notion_database_id_here
NOTION_DB_TITLE=Meeting Notes

# ========================================
# НАСТРОЙКИ АККАУНТОВ
# ========================================

# Тип аккаунта для обработки
ACCOUNT_TYPE=both  # personal, work, both, none

# Личный аккаунт
PERSONAL_CALENDAR_ID=your_personal_email@gmail.com
PERSONAL_LOCAL_DRIVE_ROOT=/Users/username/personal_foldername

# Рабочий аккаунт
WORK_CALENDAR_ID=your_work_email@company.com
WORK_LOCAL_DRIVE_ROOT=/Users/username/work_foldername

# ========================================
# МЕДИА И АНАЛИЗ
# ========================================

# Медиа обработка
MEDIA_QUALITY=medium
VIDEO_COMPRESSION=true
TRANSCRIPTION_METHOD=whisper

# OpenAI API
OPENAI_API_KEY=your_api_key
OPENAI_ANALYSIS_MODEL=gpt-4o-mini
```

### Типы аккаунтов

- **`personal`** - только личный аккаунт
- **`work`** - только рабочий аккаунт  
- **`both`** - оба аккаунта (по умолчанию)
- **`none`** - отключить все аккаунты

## 🚀 Использование
## 🔧 Последние исправления (v2.1.0)

### ✅ Устраненные критические ошибки
- **Исправлена ошибка `_create_cycle_state`** - сервис больше не падает с критической ошибкой
- **Исправлена ошибка `get_openai_config`** - генерация саммари для транскрипций работает корректно
- **Исправлена ошибка календаря** - устранена проблема с пустым URL в WebCalendarProvider
- **Стандартизированы названия файлов статуса** - единообразные названия во всей системе

### 🆕 Новые возможности
- **Скрипт `check_folders.py`** - автоматическая проверка всех папок и обновление статуса
- **Интеграция с `folder_status_monitor.py`** - функция проверки и установки корректного статуса
- **Улучшенная обработка ошибок** - более детальное логирование и восстановление

### 📁 Стандартизированные названия файлов
- `processing_status.json` - статус обработки файлов
- `processing_status.md` - текстовый отчет о статусе


### Универсальный скрипт
### Новые инструменты мониторинга

```bash
# Проверка всех папок и обновление статуса
python scripts/check_folders.py

# Мониторинг состояния папок встреч
python scripts/folder_status_monitor.py

# Проверка и установка корректного статуса
python scripts/folder_status_monitor.py --check-status
```


```bash
# Обработка медиа для всех аккаунтов
python meeting_automation_universal.py media --account both

# Обработка только личного аккаунта
python meeting_automation_universal.py media --account personal

# Обработка календарей
python meeting_automation_universal.py calendar --account work

# Полная обработка
python meeting_automation_universal.py all --verbose
```

### Системный сервис

```bash
# Запуск сервиса
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Остановка сервиса
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Проверка статуса
launchctl list | grep meeting

# Мониторинг
python ./scripts/monitor_service.py
```

### Мониторинг

```bash
# Проверка состояния сервиса
python ./scripts/monitor_service.py

# Просмотр логов
tail -f logs/service.log
tail -f logs/universal_automation.log
```

## 📊 Мониторинг состояния папок встреч

### Комплексный мониторинг

Для детального анализа состояния папок встреч используйте скрипт `folder_status_monitor.py`:

```bash
# Базовый мониторинг
python scripts/folder_status_monitor.py

# С сохранением отчета в файл
python scripts/folder_status_monitor.py --save

# С указанием пути для сохранения
python scripts/folder_status_monitor.py --save --output my_report.txt

# С отправкой в Telegram
python scripts/folder_status_monitor.py --telegram

# Комбинированный режим
python scripts/folder_status_monitor.py --save --telegram
```

#### Что показывает скрипт:

**📂 Анализ папок встреч:**
- Общее количество папок по аккаунтам
- Статус каждой папки (завершено, в процессе, не начато)
- Процент завершения обработки

**🔄 Этапы обработки:**
- 🎬 Сжатие видео
- 🎵 Извлечение аудио  
- 📝 Транскрипция
- 📋 Генерация саммари
- 🔗 Синхронизация с Notion

**📅 Интеграции:**
- Поиск событий в Google Calendar
- Поиск записей в Notion
- Связывание папок с календарными событиями

**📊 Статистика файлов:**
- Оригинальные видео
- Сжатые версии
- Аудио файлы
- Транскрипции
- Саммари
- Данные Notion

#### Пример отчета:

```
🤖 *КОМПЛЕКСНЫЙ ОТЧЕТ О СОСТОЯНИИ ПАПОК ВСТРЕЧ*

👥 *PERSONAL АККАУНТ*
📁 Всего папок: 2

📂 *2025-08-21 18-00 Тестовая встреча*
   🎯 Статус: 🟡 near_completion
   📊 Прогресс: 80%
   🔄 Этапы обработки:
      🎬 Видео: ✅ completed
      🎵 Аудио: ✅ completed
      📝 Транскрипция: ✅ completed
      📋 Саммари: ✅ completed
      🔗 Notion: ❌ not_started
```

#### Автоматизация:

Добавьте в cron для регулярного мониторинга:

```bash
# Каждые 5 минут
*/5 * * * * cd /path/to/meeting_automation && python scripts/folder_status_monitor.py --save --telegram

# Каждый час
0 * * * * cd /path/to/meeting_automation && python scripts/folder_status_monitor.py --save
```

## 🚀 Запуск как системный сервис

### macOS (launchctl)

Для запуска как системный сервис на macOS используйте `launchctl`:

#### 1. Создание plist файла

Создайте файл `~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yazydzhi.meeting-automation</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/azg/repository/meeting_automation/venv/bin/python</string>
        <string>/Users/azg/repository/meeting_automation/src/service_manager.py</string>
        <string>--interval</string>
        <string>300</string>
        <string>--media-interval</string>
        <string>1800</string>
        <string>--log-level</string>
        <string>INFO</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/azg/repository/meeting_automation</string>
    
    <key>StandardOutPath</key>
    <string>/Users/azg/repository/meeting_automation/logs/service.log</string>
    
    <key>StandardErrorPath</key>
    <string>/Users/azg/repository/meeting_automation/logs/service_error.log</string>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

#### 2. Загрузка и запуск сервиса

```bash
# Загрузить сервис
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Проверить статус
launchctl list | grep meeting-automation

# Остановить сервис
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
```

#### 3. Параметры запуска

**Обязательные параметры:**
- `--interval 300` - интервал проверки календаря (5 минут)
- `--media-interval 1800` - интервал медиа обработки (30 минут)

**Дополнительные параметры:**
- `--log-level INFO` - уровень логирования (DEBUG, INFO, WARNING, ERROR)
- `--config .env` - путь к файлу конфигурации

**Пример запуска:**
```bash
# Базовый запуск
python src/service_manager.py --interval 300 --media-interval 1800

# С дополнительными параметрами
python src/service_manager.py --interval 300 --media-interval 1800 --log-level DEBUG --config .env.custom
```

#### 4. Мониторинг

```bash
# Проверка статуса
python ./scripts/monitor_service.py

# Просмотр логов
tail -f logs/service.log
tail -f logs/service_error.log
```

### Linux (systemd)

Для Linux создайте файл `/etc/systemd/system/meeting-automation.service`:

```ini
[Unit]
Description=Meeting Automation Service
After=network.target

[Service]
Type=simple
User=azg
WorkingDirectory=/path/to/meeting_automation
Environment=PATH=/path/to/meeting_automation/venv/bin
ExecStart=/path/to/meeting_automation/venv/bin/python src/service_manager.py --interval 300 --media-interval 1800 --log-level INFO
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable meeting-automation
sudo systemctl start meeting-automation
sudo systemctl status meeting-automation
```

## 🔧 Оптимизация и производительность

### Кэширование результатов

Система использует кэширование для оптимизации производительности:

- **Кэш обработанных файлов** - хранится в `data/service_cache.json`
- **Кэш транскрибированных файлов** - предотвращает повторную транскрипцию
- **Кэш проанализированных файлов** - предотвращает повторный анализ
- **Кэш страниц Notion** - ускоряет синхронизацию с Notion

### Параллельная обработка

Система использует параллельную обработку для независимых операций:

- **Обработка аккаунтов** - личный и рабочий аккаунты обрабатываются параллельно
- **Отправка уведомлений** - происходит параллельно с созданием файлов статуса
- **Медиа обработка** - может обрабатывать несколько файлов параллельно

### Мониторинг производительности

Система ведет мониторинг производительности:

- **CPU** - отслеживает использование процессора
- **Память** - отслеживает использование памяти
- **Диск** - отслеживает использование диска
- **Время выполнения** - отслеживает время выполнения каждого этапа

Статистика сохраняется в `data/performance_stats.json` и доступна для анализа.

## 🔧 Установка

1. **Клонирование репозитория**
   ```bash
   git clone <repository_url>
   cd meeting_automation
   ```

2. **Создание виртуального окружения**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   ```

3. **Установка зависимостей**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройка конфигурации**
   ```bash
   cp .env.example .env
   # Отредактируйте .env файл под ваши нужды
   ```

5. **Настройка системного сервиса**
   ```bash
   # Скопируйте plist файл в LaunchAgents
   cp com.yazydzhi.meeting-automation.plist ~/Library/LaunchAgents/
   
   # Запустите сервис
   launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
   ```

## 📋 Поддерживаемые провайдеры

### Календари
- **Google Calendar API** - прямая интеграция
- **iCal (web)** - загрузка по URL
- **Notion** - база данных событий
- **Локальные файлы** - ICS, JSON

### Google Drive
- **Google Drive API** - прямая интеграция
- **Локальные папки** - синхронизация файлов
- **Google Drive Desktop** - интеграция с десктопным приложением

### Транскрипция
- **Whisper (локально)** - быстрая обработка
- **OpenAI API** - высокое качество
- **Поддержка русского языка**

## 🐛 Устранение неполадок

### Проблемы с конфигурацией
```bash
# Проверка конфигурации
python -c "from src.config_manager import ConfigManager; config = ConfigManager(); print(config.get_config_summary())"

# Проверка валидности конфигурации
python -c "from src.config_manager import ConfigManager; config = ConfigManager(); print(config.validate_config())"
```

### Проблемы с сервисом
```bash
# Проверка процессов
ps aux | grep meeting

# Перезапуск сервиса
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Проверка логов
tail -f logs/service.log
```

### Проблемы с медиа
```bash
# Проверка ffmpeg
ffmpeg -version

# Очистка зависших процессов
pkill -f ffmpeg

# Проверка статуса кэша
python -c "import json; print(json.load(open('data/service_cache.json')))"

# Очистка кэша (в случае проблем)
rm data/service_cache.json
```

### Проблемы с транскрипцией
```bash
# Проверка наличия аудио файлов
find /path/to/meetings -name "*.mp3" | grep -v "_compressed"

# Запуск транскрипции для конкретного файла
python meeting_automation_universal.py transcribe --file /path/to/audio.mp3

# Проверка статуса транскрипции
python -c "from src.service_manager import MeetingAutomationService; service = MeetingAutomationService(); print(service.process_audio_transcription())"
```

### Проблемы с производительностью
```bash
# Проверка статистики производительности
python -c "import json; print(json.load(open('data/performance_stats.json')))"

# Мониторинг ресурсов в реальном времени
top -o cpu  # Сортировка по CPU
top -o mem  # Сортировка по памяти

# Проверка использования диска
du -sh /path/to/meeting_automation
```

### Сброс состояния сервиса
```bash
# Остановка сервиса
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Очистка кэша и состояния
rm -f data/service_cache.json data/service_state.json data/performance_stats.json

# Запуск сервиса заново
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
```

## 📝 Логирование

Система ведет подробные логи:

- **`logs/service.log`** - основной лог сервиса
- **`logs/universal_automation.log`** - лог универсального скрипта
- **`logs/personal_automation.log`** - лог личного аккаунта
- **`logs/work_automation.log`** - лог рабочего аккаунта

## 🔒 Безопасность

- Все API ключи хранятся в `.env` файле
- Файл `.env` добавлен в `.gitignore`
- Поддержка различных провайдеров для обхода блокировок
- Локальная обработка медиа без отправки в облако

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

Проект распространяется под лицензией MIT.

---

**🎯 Цель проекта**: Автоматизация рутинных задач по обработке встреч и медиа файлов для повышения продуктивности.
