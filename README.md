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
│   ├── calendar_processor.py     # Обработчик календарей
│   ├── drive_processor.py        # Обработчик Google Drive
│   ├── media_processor.py        # Обработчик медиа
│   └── notion_processor.py       # Обработчик Notion
├── scripts/
│   └── monitor_service.py        # Мониторинг сервиса
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

### Универсальный скрипт

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
```

### Проблемы с сервисом
```bash
# Проверка процессов
ps aux | grep meeting

# Перезапуск сервиса
launchctl unload ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
launchctl load ~/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist
```

### Проблемы с медиа
```bash
# Проверка ffmpeg
ffmpeg -version

# Очистка зависших процессов
python -c "from src.service_manager import MeetingAutomationService; service = MeetingAutomationService(); service._kill_hanging_ffmpeg_processes()"
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
