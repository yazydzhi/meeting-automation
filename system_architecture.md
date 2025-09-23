# Архитектура системы автоматизации встреч

## Общая структура

```
📁 meeting_automation_universal.py (главный скрипт)
📁 src/
    ├── 📁 config_manager.py (управление конфигурацией)
    ├── 📁 service_manager.py (основной сервис)
    ├── 📁 telegram_api.py (API Telegram)
    ├── 📁 prompt_manager.py (управление промптами)
    ├── 📁 notion_templates.py (шаблоны Notion)
    └── 📁 handlers/
        ├── 📁 base_handler.py (базовый класс)
        ├── 📁 process_handler.py (обработка файлов)
        ├── 📁 account_handler.py (обработка аккаунтов)
        ├── 📁 calendar_handler.py (календарь)
        ├── 📁 calendar_integration_handler.py (интеграция календаря)
        ├── 📁 media_handler.py (медиа файлы)
        ├── 📁 transcription_handler.py (транскрипция)
        ├── 📁 summary_handler.py (саммари)
        ├── 📁 notion_handler.py (Notion)
        ├── 📁 notion_api.py (API Notion)
        ├── 📁 metrics_handler.py (метрики)
        ├── 📁 state_manager.py (управление состоянием)
        └── 📁 smart_report_generator.py (умные отчеты)
```

## Компоненты системы

### 🎯 Основные компоненты

#### 1. **MeetingAutomationService** (service_manager.py)
- **Роль**: Главный координатор системы
- **Функции**:
  - Управление жизненным циклом сервиса
  - Координация всех этапов обработки
  - Мониторинг производительности
  - Управление кэшем и состоянием

#### 2. **ConfigManager** (config_manager.py)
- **Роль**: Централизованное управление конфигурацией
- **Функции**:
  - Загрузка переменных окружения
  - Валидация настроек
  - Предоставление конфигурации компонентам

#### 3. **StateManager** (handlers/state_manager.py)
- **Роль**: Управление состоянием и данными
- **Функции**:
  - SQLite база данных для отслеживания состояния
  - Предотвращение дублирования обработки
  - Хранение метаданных событий

### 🔧 Обработчики (Handlers)

#### **BaseHandler** (handlers/base_handler.py)
- **Роль**: Базовый класс для всех обработчиков
- **Функции**:
  - Общие методы логирования
  - Декоратор retry для повторных попыток
  - Стандартные методы создания результатов

#### **CalendarIntegrationHandler** (handlers/calendar_integration_handler.py)
- **Роль**: Интеграция календаря с файловой системой
- **Функции**:
  - Получение событий календаря
  - Создание папок встреч
  - Создание страниц Notion
  - Связывание событий с папками

#### **MediaHandler** (handlers/media_handler.py)
- **Роль**: Обработка медиа файлов
- **Функции**:
  - Сжатие видео через FFmpeg
  - Извлечение аудио
  - Умное именование файлов
  - Управление оригинальными файлами

#### **TranscriptionHandler** (handlers/transcription_handler.py)
- **Роль**: Транскрипция аудио
- **Функции**:
  - Транскрипция через Whisper
  - Создание файлов транскрипции
  - Обработка метаданных

#### **SummaryHandler** (handlers/summary_handler.py)
- **Роль**: Генерация саммари
- **Функции**:
  - Анализ транскрипций через OpenAI
  - Создание индивидуальных саммари
  - Создание комплексных саммари для множественных видео

#### **NotionHandler** (handlers/notion_handler.py)
- **Роль**: Интеграция с Notion
- **Функции**:
  - Создание страниц встреч
  - Обновление страниц результатами
  - Синхронизация контента

### 📊 Вспомогательные компоненты

#### **SmartReportGenerator** (handlers/smart_report_generator.py)
- **Роль**: Генерация умных отчетов
- **Функции**:
  - Анализ изменений в системе
  - Формирование детальных отчетов
  - Определение необходимости уведомлений

#### **TelegramAPI** (telegram_api.py)
- **Роль**: Интеграция с Telegram
- **Функции**:
  - Отправка уведомлений
  - Форматирование сообщений

## Потоки данных

### 📥 Входящие данные
```
Календарь (Google/Outlook) → CalendarHandler → CalendarIntegrationHandler
Медиа файлы → MediaHandler
Аудио файлы → TranscriptionHandler
Транскрипции → SummaryHandler
```

### 📤 Исходящие данные
```
CalendarIntegrationHandler → Папки встреч + Notion страницы
MediaHandler → Сжатые видео + аудио файлы
TranscriptionHandler → Файлы транскрипции
SummaryHandler → Саммари + анализ
NotionHandler → Обновленные страницы Notion
TelegramAPI → Уведомления в Telegram
```

### 💾 Хранение данных
```
StateManager (SQLite) ← Все обработчики
Кэш файлов (JSON) ← ServiceManager
Логи (RotatingFileHandler) ← Все компоненты
```

## Интеграции

### 🔗 Внешние сервисы
- **Google Calendar API**: Получение событий календаря
- **Google Drive API**: Доступ к файлам встреч
- **Notion API**: Создание и обновление страниц
- **OpenAI API**: Генерация саммари
- **Telegram Bot API**: Отправка уведомлений
- **Whisper**: Транскрипция аудио
- **FFmpeg**: Обработка медиа файлов

### 🗄️ Локальные ресурсы
- **SQLite**: База данных состояния
- **Файловая система**: Папки встреч и файлы
- **Кэш**: JSON файлы для быстрого доступа

## Конфигурация

### ⚙️ Переменные окружения (.env)
```
# Общие настройки
SERVICE_CHECK_INTERVAL=300
SERVICE_MEDIA_INTERVAL=1800
TIMEZONE=Europe/Moscow

# Личный аккаунт
PERSONAL_ENABLED=true
PERSONAL_CALENDAR_PROVIDER=google
PERSONAL_DRIVE_PROVIDER=google
PERSONAL_LOCAL_DRIVE_ROOT=/path/to/personal

# Рабочий аккаунт
WORK_ENABLED=true
WORK_CALENDAR_PROVIDER=google
WORK_DRIVE_PROVIDER=google
WORK_LOCAL_DRIVE_ROOT=/path/to/work

# Notion
NOTION_TOKEN=your_token
NOTION_DATABASE_ID=your_database_id

# OpenAI
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Медиа
MEDIA_QUALITY=medium
DELETE_ORIGINAL_VIDEOS=false

# Саммари
ENABLE_GENERAL_SUMMARY=true
ENABLE_COMPLEX_SUMMARY=true
```

## Безопасность и надежность

### 🛡️ Защита от ошибок
- Декоратор `@retry` для повторных попыток
- Проверка существования файлов и папок
- Валидация конфигурации при запуске
- Graceful handling исключений

### 📊 Мониторинг
- Детальное логирование всех операций
- Мониторинг производительности системы
- Статистика выполнения циклов
- Отслеживание ошибок и предупреждений

### 🔄 Восстановление
- Сохранение состояния после каждого цикла
- Кэширование обработанных файлов
- Возможность продолжения с места остановки
- Ротация логов для предотвращения переполнения