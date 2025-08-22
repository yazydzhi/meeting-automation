# 🚀 Система автоматизации встреч

Полноценная система автоматизации встреч для личного и рабочего аккаунтов с поддержкой Google Calendar, Notion, Google Drive и Telegram.

## ✨ Возможности

### 🔄 Автоматизация встреч
- **Автоматическое создание заметок** и папок в Notion и Google Drive
- **Создание страниц с готовыми шаблонами** для удобного ведения заметок
- **Линковка заметок** с соответствующими событиями в календаре
- **Организация файлов** и документов по встречам для удобного доступа
- **Умная фильтрация событий** (исключение дней рождения, личных дел)
- **Автоматическое форматирование названий папок** в формате YYYY-MM-DD hh-mm Название
- **Предотвращение дублирования** папок Google Drive и страниц Notion

### 🎬 Обработка медиа
- **Обработка видео и аудио записей** встреч с автоматической компрессией
- **Компрессия видео файлов** с поддержкой кодеков H.264, H.265, VP9
- **4 уровня качества** сжатия: low, medium, high, ultra
- **Автоматическое сжатие** файлов больше 50MB перед конвертацией в аудио
- **Загрузка сжатых видео** в Google Drive для экономии места
- **Транскрибация аудио** в текст с помощью встроенных моделей
- **Автоматическое создание кратких саммари** по содержанию встреч

### 🔄 Поддержка двух аккаунтов
- **Личный аккаунт**: Использует стандартные Google API провайдеры
- **Рабочий аккаунт**: Использует альтернативные провайдеры (iCal, Google Drive Desktop)
- **Универсальный скрипт**: Запускает обработку для обоих аккаунтов
- **Обход корпоративных ограничений** для рабочего аккаунта

### 📱 Уведомления и мониторинг
- **Красивые отчеты в Telegram** с эмодзи и Markdown форматированием
- **Умные уведомления** - только при наличии изменений
- **Мониторинг состояния** и производительности
- **Детальные логи** всех операций

### 🏗️ Системный сервис
- **Автоматическая работа** - запуск при загрузке системы
- **Планировщик задач** - настраиваемые интервалы проверки
- **Кроссплатформенность** - поддержка macOS и Linux

## 🏗️ Архитектура

```
meeting_automation/
├── meeting_automation_work.py      # Скрипт для рабочего аккаунта
├── meeting_automation_personal.py  # Скрипт для личного аккаунта
├── meeting_automation_universal.py # Универсальный скрипт
├── src/
│   ├── calendar_alternatives.py    # Альтернативные провайдеры календаря
│   ├── drive_alternatives.py       # Альтернативные провайдеры Google Drive
│   ├── config_manager.py           # Менеджер конфигурации
│   ├── service_manager.py          # Основной сервис
│   ├── media_processor.py          # Обработка медиа + компрессия видео
│   ├── drive_sync.py              # Синхронизация Drive
│   └── notion_templates.py        # Шаблоны Notion
├── config/
│   └── personal_exclusions.txt     # Исключения для личных событий
├── tools/                          # Вспомогательные инструменты
├── tests/                          # Тестовые файлы
├── scripts/                        # Скрипты управления сервисом
├── systemd/                        # Linux systemd
├── launchd/                        # macOS launchd
└── templates/                      # Шаблоны Notion
```

## 🚀 Быстрый старт

### 1. Подготовка окружения

```bash
# Клонируйте репозиторий
git clone <repository-url>
cd meeting_automation

# Создайте виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate.bat

# Установите зависимости
pip install -r requirements.txt
```

### 2. Настройка конфигурации

#### Личный аккаунт (`env.personal`)
```bash
# Google API (стандартный способ)
GOOGLE_CREDENTIALS=creds/client_secret.json
PERSONAL_CALENDAR_ID=yazydzhi@gmail.com
PERSONAL_DRIVE_PARENT_ID=your_drive_folder_id

# Notion
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Провайдеры (API для личного)
CALENDAR_PROVIDER=google_api
DRIVE_PROVIDER=google_api
```

#### Рабочий аккаунт (`env.work`)
```bash
# Google API (может быть заблокирован)
GOOGLE_CREDENTIALS=creds/work_client_secret.json
WORK_CALENDAR_ID=work@company.com
WORK_DRIVE_PARENT_ID=work_folder_id

# Notion
NOTION_TOKEN=work_notion_token
NOTION_DATABASE_ID=work_database_id

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=work_chat_id

# Провайдеры (альтернативы для рабочего)
CALENDAR_PROVIDER=web_ical
DRIVE_PROVIDER=google_desktop

# Альтернативные настройки
ICAL_CALENDAR_URL=https://calendar.google.com/ical/work@company.com/basic.ics
GOOGLE_DRIVE_DESKTOP_PATH=/Users/username/Google Drive (Work)
```

### 3. Создание ресурсов

```bash
# Создание базы данных в Notion
python tools/create_notion_db.py

# Инициализация проекта
python tools/init_project.py prepare
```

## 📖 Использование

### Основные команды

#### **Обработка календаря**
```bash
# Рабочий аккаунт (7 дней, подробно)
python meeting_automation_work.py prepare --days 7 --verbose

# Личный аккаунт (5 дней)
python meeting_automation_personal.py prepare --days 5

# Оба аккаунта через universal
python meeting_automation_universal.py prepare --days 3 --verbose
```

#### **Обработка медиа файлов**
```bash
# Обработка медиа с компрессией видео
python meeting_automation_personal.py media

# Обработка медиа для рабочего аккаунта
python meeting_automation_work.py media
```

#### **Тестирование**
```bash
# Только проверка конфигурации
python meeting_automation_work.py test --config-only

# Только проверка календаря
python meeting_automation_personal.py test --calendar-only

# Только проверка Google Drive
python meeting_automation_universal.py test --drive-only --work-only

# Полное тестирование
python meeting_automation_universal.py test --verbose
```

### Поддерживаемые аргументы

#### **Основные команды:**
- `prepare` - обработка календаря
- `media` - обработка медиа файлов
- `test` - тестирование провайдеров

#### **Общие аргументы:**
- `--days N` - количество дней для обработки (по умолчанию: 2 для personal, 3 для work)
- `--verbose` - подробный режим логирования
- `--folders N` - максимум папок для обработки
- `--cleanup` - очистка старых файлов

#### **Тестовые аргументы:**
- `--config-only` - только проверка конфигурации
- `--calendar-only` - только проверка календаря
- `--drive-only` - только проверка Google Drive

#### **Universal скрипт дополнительно поддерживает:**
- `--personal-only` - только личный аккаунт
- `--work-only` - только рабочий аккаунт
- `--skip-config-check` - пропустить проверку конфигураций

## 🔧 Управление сервисом

### Установка сервиса

```bash
# Сделайте скрипты исполняемыми
chmod +x scripts/*.sh

# Установите сервис
./scripts/install_service.sh
```

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
./scripts/service_control.sh status

# Мониторинг
python scripts/monitor_service.py
```

## 📋 Шаблоны страниц

Система автоматически создает страницы в Notion с готовыми шаблонами, включающими:

- 📋 **Заголовок встречи** с названием
- ⏰ **Время начала и окончания**
- 👥 **Список участников**
- 🎯 **Секция для целей встречи**
- 📝 **Секция для заметок**
- ✅ **Секция для действий (to-do)**
- 🔗 **Ссылки на Google Drive и встречу**
- 📅 **Секция для следующих шагов**

Шаблоны можно редактировать в файле `templates/meeting_page_template.json`.

## 🎬 Настройки компрессии видео

```bash
# Включить/выключить компрессию видео
VIDEO_COMPRESSION=true

# Качество сжатия: low, medium, high, ultra
VIDEO_QUALITY=high

# Кодек для сжатия: h264, h265, vp9
VIDEO_CODEC=h264
```

## 🔄 Поддержка RRULE событий

Система автоматически обрабатывает повторяющиеся события (RRULE) из iCal календарей:

- **Еженедельные встречи** (FREQ=WEEKLY)
- **Ежемесячные события** (FREQ=MONTHLY)
- **Ежедневные повторения** (FREQ=DAILY)
- **Настраиваемые интервалы** (INTERVAL)
- **Даты окончания** (UNTIL)
- **Дни недели** (BYDAY)

## 📁 Конфигурируемые исключения

Создайте файл `config/personal_exclusions.txt` для настройки исключений:

```
# Личные события - исключаются из обработки
День рождения
Дела
Личное
Personal
Отпуск
обед
lunch
```

## 🧪 Тестирование

### Запуск тестов

```bash
# Тесты Notion
python tests/test_notion_work.py

# Тесты альтернативных провайдеров
python tests/test_alternative_providers.py

# Тесты сжатия видео
python tests/test_video_compression.py

# Тесты обработки медиа
python tests/test_media_processing.py
```

### Проверка конфигурации

```bash
# Проверка всех провайдеров
python tests/test_alternative_providers.py

# Проверка Google Drive
python tests/test_google_drive_detailed.py

# Быстрая проверка API
python tests/test_quick_api_check.py
```

## 📊 Мониторинг и логи

### Логи системы

```
logs/
├── personal_automation.log    # Логи личного аккаунта
├── work_automation.log        # Логи рабочего аккаунта
├── universal_automation.log   # Логи универсального скрипта
└── service.log               # Логи системного сервиса
```

### Мониторинг производительности

```bash
# Запуск мониторинга
python scripts/monitor_service.py

# Просмотр статистики
tail -f logs/service.log | grep "STATS"
```

## 🚨 Устранение неполадок

### Частые проблемы

1. **Ошибки Google API**
   - Проверьте файл учетных данных
   - Убедитесь, что API включены в Google Console

2. **Проблемы с Notion**
   - Проверьте токен доступа
   - Убедитесь, что база данных существует

3. **Ошибки синхронизации**
   - Проверьте права доступа к папкам
   - Убедитесь, что провайдеры настроены корректно

### Отладка

```bash
# Подробный режим логирования
python meeting_automation_work.py prepare --verbose

# Только проверка конфигурации
python meeting_automation_personal.py test --config-only

# Проверка конкретного провайдера
python meeting_automation_work.py test --calendar-only
```

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Создайте Pull Request

## 📄 Лицензия

Этот проект распространяется под лицензией MIT.

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи в папке `logs/`
2. Запустите тесты: `python meeting_automation_work.py test --verbose`
3. Создайте Issue в репозитории с описанием проблемы

---

**Система автоматизации полностью готова к использованию!** 🎉
