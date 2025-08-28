# 🚀 Meeting Automation System

Система автоматизации встреч с поддержкой личного и рабочего аккаунтов через единую конфигурацию.

## ✨ Основные возможности

- **📅 Автоматическая обработка календарей** (iCal, Google Calendar API)
- **💾 Синхронизация с Google Drive** (API и локальные папки)
- **📝 Интеграция с Notion** для заметок о встречах
- **🎬 Обработка медиа файлов** (сжатие видео, извлечение аудио)
- **🎤 Транскрипция аудио** (Whisper, OpenAI API)
- **🤖 Анализ транскрипций** через OpenAI GPT
- **📱 Умные уведомления в Telegram** (только при изменениях)
- **⚙️ Единая конфигурация** для всех аккаунтов
- **🧠 Система кэширования** для предотвращения повторной обработки
- **📊 Умные отчеты** с группировкой по папкам встреч

## 🏗️ Архитектура

```
meeting_automation/
├── .env                          # Единая конфигурация
├── meeting_automation_universal.py  # Универсальный CLI скрипт
├── src/
│   ├── config_manager.py         # Менеджер конфигурации
│   ├── service_manager.py        # Системный сервис
│   ├── handlers/                 # Модульные обработчики
│   │   ├── account_handler.py    # Обработчик аккаунтов
│   │   ├── media_handler.py      # Обработчик медиа файлов
│   │   ├── transcription_handler.py  # Обработчик транскрипций
│   │   ├── summary_handler.py    # Обработчик саммари
│   │   ├── notion_handler.py     # Интеграция с Notion
│   │   ├── telegram_api.py       # API для Telegram
│   │   ├── smart_report_generator.py  # Умный генератор отчетов
│   │   └── metrics_handler.py    # Обработчик метрик
│   ├── calendar_handler.py       # Обработчик календарей
│   └── transcript_analyzer.py    # Анализатор транскрипций
├── scripts/
│   ├── start_service.sh          # Запуск сервиса
│   ├── stop_service.sh           # Остановка сервиса
│   ├── monitor_service.py        # Мониторинг сервиса
│   ├── folder_status_monitor.py  # Мониторинг папок встреч
│   ├── check_folders.py          # Проверка и обновление статуса папок
│   ├── cleanup_backups.py        # Очистка резервных копий
│   ├── log_manager.py            # Управление логами
│   └── cron_log_cleanup.py      # Автоматическая очистка логов
├── data/                         # Данные кэша и статистики
│   ├── service_cache.json        # Кэш обработанных файлов
│   └── service_state.json        # Состояние сервиса
├── logs/                         # Логи системы
└── memory-bank/                  # Система памяти и документации
```

## 🆕 Последние изменения (v2.2.0)

### 🧠 Умная система уведомлений
- **SmartReportGenerator** - генерирует отчеты только при реальных изменениях
- **Группировка по папкам встреч** - информация структурирована по названиям встреч
- **Умная логика изменений** - отчеты не отправляются при повторной обработке тех же файлов
- **Формат отчетов** - структурированные сообщения с эмодзи и группировкой

### 🔧 Улучшения обработки медиа
- **Умное именование файлов** - `Folder_Name_compressed.mp4`, `Folder_Name_2_compressed.mp4`
- **Автоматическое удаление оригиналов** - после проверки длительности видео
- **Система кэширования** - предотвращает повторную обработку файлов
- **Статусные файлы** - `processing_status.md` в каждой папке встречи

### 🚀 Архитектурные улучшения
- **Модульная архитектура** - переход от монолитных скриптов к обработчикам
- **Универсальный CLI** - `meeting_automation_universal.py` для всех операций
- **Исправление дублирования логов** - устранена проблема множественных хендлеров
- **Оптимизация производительности** - улучшена обработка ошибок и восстановление

### 📱 Улучшения Telegram
- **Условная отправка** - только при изменениях или ошибках
- **Структурированные отчеты** - группировка по встречам, время выполнения, статус
- **Обработка ошибок** - уведомления о новых ошибках в логах

## 🚀 Запуск сервиса

### Ручное управление (рекомендуется)

```bash
# Запуск сервиса
./scripts/start_service.sh

# Остановка сервиса
./scripts/stop_service.sh

# Проверка статуса
ps aux | grep service_manager
cat data/service.pid
```

### Автоматический запуск через launchctl (macOS)

```bash
# Загрузка сервиса
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Выгрузка сервиса
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist

# Проверка статуса
launchctl list | grep meeting
```

**Примечание:** На некоторых версиях macOS могут возникать проблемы с launchctl. В этом случае рекомендуется использовать ручное управление через скрипты.

## ⚙️ Конфигурация
### Настройки логирования

```bash
# Логирование
LOG_LEVEL=INFO                    # Уровень логирования
LOG_RETENTION_DAYS=30            # Время хранения логов (дни)
LOG_MAX_SIZE_MB=100              # Максимальный размер файла (MB)
LOG_BACKUP_COUNT=5               # Количество резервных копий
LOG_ROTATION_ENABLED=true        # Включение ротации
```

**Параметры логирования:**
- **`LOG_LEVEL`** - уровень детализации логов (INFO, DEBUG, WARNING, ERROR)
- **`LOG_RETENTION_DAYS`** - автоматическое удаление логов старше указанного количества дней
- **`LOG_MAX_SIZE_MB`** - максимальный размер лог файла перед ротацией
- **`LOG_BACKUP_COUNT`** - количество резервных копий при ротации
- **`LOG_ROTATION_ENABLED`** - включение/отключение автоматической ротации


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
### Инструменты управления логами

```bash
# Анализ состояния логов
python scripts/log_manager.py --action analyze

# Полная оптимизация логов
python scripts/log_manager.py --action optimize

# Ротация больших файлов
python scripts/log_manager.py --action rotate

# Очистка старых логов
python scripts/log_manager.py --action cleanup

# Автоматическая очистка через cron
python scripts/cron_log_cleanup.py
```

**Возможности log_manager.py:**
- 📊 Анализ текущего состояния логов
- 🔄 Автоматическая ротация больших файлов
- 🗑️ Очистка логов по времени хранения
- 🔍 Поиск и удаление дублирующих файлов
- ⚙️ Настройка параметров через .env


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
ps aux | grep service_manager
cat data/service.pid

# Запуск/остановка сервиса
./scripts/start_service.sh
./scripts/stop_service.sh

# Перезапуск сервиса (если используете launchctl)
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
./scripts/stop_service.sh

# Очистка кэша и состояния
rm -f data/service_cache.json data/service_state.json data/performance_stats.json data/service.pid

# Запуск сервиса заново
./scripts/start_service.sh

# Альтернативно через launchctl (если используете)
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
```

## 🛠️ Утилиты и скрипты

### Управление сервисом
- **`start_service.sh`** - Запуск сервиса с проверкой дублирования процессов
- **`stop_service.sh`** - Корректная остановка сервиса и очистка PID файла

### Мониторинг и обслуживание
- **`check_folders.py`** - Проверка и обновление статуса обработки папок встреч
- **`cleanup_backups.py`** - Очистка временных резервных копий файлов
- **`log_manager.py`** - Анализ, оптимизация и управление логами системы
- **`cron_log_cleanup.py`** - Автоматическая очистка логов по расписанию

### Мониторинг сервиса
- **`monitor_service.py`** - Мониторинг состояния сервиса
- **`folder_status_monitor.py`** - Мониторинг статуса папок встреч

## 📝 Логирование

Система ведет подробные логи с автоматической ротацией:

- **`logs/service.log`** - основной лог сервиса (с ротацией)
- **`logs/universal_automation.log`** - лог универсального скрипта
- **`logs/personal_automation.log`** - лог личного аккаунта
- **`logs/work_automation.log`** - лог рабочего аккаунта

**Настройки логирования:**
- Автоматическая ротация при достижении максимального размера
- Настраиваемое время хранения логов
- Консольный вывод для отладки

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
