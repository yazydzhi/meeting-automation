# 🔄 Альтернативные провайдеры календаря и Google Drive

Этот документ описывает альтернативные способы взаимодействия с календарем и Google Drive, которые можно использовать, когда стандартные API недоступны или заблокированы.

## 🎯 Проблема

В корпоративной среде часто возникают ограничения:
- **Google Calendar API заблокирован** организацией
- **Google Drive API недоступен** из-за политик безопасности
- **Приложения не могут получить доступ** к корпоративным ресурсам

## ✅ Решение

Система поддерживает **модульную архитектуру** с различными провайдерами:

```bash
# В .env файле указываем нужные провайдеры
CALENDAR_PROVIDER=notion          # или web_ical, local_json
DRIVE_PROVIDER=google_desktop     # или local
```

## 📅 Альтернативные провайдеры календаря

### 1. **Notion календарь** (`notion`)
Использует базу данных Notion как источник событий.

**Преимущества:**
- ✅ Полный контроль над данными
- ✅ Богатые возможности форматирования
- ✅ Интеграция с существующими заметками

**Настройка:**
```bash
CALENDAR_PROVIDER=notion
NOTION_TOKEN=your_notion_token
NOTION_CALENDAR_DATABASE_ID=your_database_id
```

**Структура базы данных:**
- `Название` (title) - название встречи
- `Дата` (date) - дата и время начала
- `Описание` (rich_text) - описание встречи
- `Место` (rich_text) - место проведения
- `Участники` (multi_select) - список участников
- `Ссылка` (url) - ссылка на встречу

### 2. **Веб-календарь iCal** (`web_ical`)
Получает события из публичных iCal ссылок.

**Преимущества:**
- ✅ Работает с любыми календарями
- ✅ Не требует API ключей
- ✅ Стандартный формат

**Настройка:**
```bash
CALENDAR_PROVIDER=web_ical
ICAL_CALENDAR_URL=https://calendar.google.com/calendar/ical/your_calendar_id/basic.ics
```

**Получение iCal ссылки:**
1. Откройте Google Calendar
2. Настройки календаря → Интеграция календаря
3. Скопируйте "Ссылку iCal"

### 3. **Веб-календарь RSS** (`web_rss`)
Получает события из RSS лент календаря.

**Настройка:**
```bash
CALENDAR_PROVIDER=web_rss
RSS_CALENDAR_URL=https://calendar.google.com/calendar/feeds/your_calendar_id/public/basic
```

### 4. **Локальный iCal файл** (`local_ics`)
Читает события из локального .ics файла.

**Настройка:**
```bash
CALENDAR_PROVIDER=local_ics
LOCAL_ICS_FILE=data/calendar/events.ics
```

**Создание .ics файла:**
```bash
# Экспорт из Google Calendar
# Или создание вручную
BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:Название встречи
DTSTART:20250822T100000
DTEND:20250822T110000
DESCRIPTION:Описание встречи
LOCATION:Место проведения
END:VEVENT
END:VCALENDAR
```

### 5. **Локальный JSON файл** (`local_json`)
Читает события из локального JSON файла.

**Настройка:**
```bash
CALENDAR_PROVIDER=local_json
LOCAL_JSON_FILE=data/calendar/events.json
```

**Структура JSON:**
```json
{
  "events": [
    {
      "title": "Название встречи",
      "start": "2025-08-22T10:00:00",
      "end": "2025-08-22T11:00:00",
      "description": "Описание встречи",
      "location": "Место проведения",
      "attendees": ["user1@example.com", "user2@example.com"],
      "meeting_link": "https://meet.google.com/abc-defg-hij"
    }
  ]
}
```

## 💾 Альтернативные провайдеры Google Drive

### 1. **Google Drive для Desktop** (`google_desktop`)
Работает с локально синхронизированными файлами.

**Преимущества:**
- ✅ Полный доступ к файлам
- ✅ Автоматическая синхронизация
- ✅ Работает без API

**Настройка:**
```bash
DRIVE_PROVIDER=google_desktop
GOOGLE_DRIVE_DESKTOP_PATH=/Users/username/Google Drive
```

**Установка Google Drive для Desktop:**
1. Скачайте с [drive.google.com](https://drive.google.com)
2. Установите и настройте синхронизацию
3. Укажите путь к папке синхронизации

### 2. **Локальная файловая система** (`local`)
Работает с локальными папками.

**Преимущества:**
- ✅ Полный контроль над файлами
- ✅ Быстрая работа
- ✅ Не зависит от интернета

**Настройка:**
```bash
DRIVE_PROVIDER=local
LOCAL_DRIVE_ROOT=data/local_drive
```

**Структура папок:**
```
data/local_drive/
├── 2025-08-22 10-00 Встреча 1/
│   ├── notes.txt
│   └── presentation.pdf
└── 2025-08-23 14-00 Встреча 2/
    ├── agenda.md
    └── recording.mp4
```

## 🔧 Настройка системы

### 1. **Создание .env файла**
```bash
# Запустите тест для создания примера
python test_alternative_providers.py
```

### 2. **Выбор провайдеров**
```bash
# Календарь
CALENDAR_PROVIDER=notion          # или web_ical, local_json
DRIVE_PROVIDER=google_desktop     # или local

# Настройки для выбранных провайдеров
NOTION_TOKEN=your_token
NOTION_CALENDAR_DATABASE_ID=your_db_id
GOOGLE_DRIVE_DESKTOP_PATH=/path/to/drive
```

### 3. **Проверка конфигурации**
```bash
# Запустите тест для проверки
python test_alternative_providers.py
```

## 📊 Сравнение провайдеров

### Календарь

| Провайдер | Сложность | Функциональность | Надежность |
|-----------|-----------|------------------|------------|
| `google_api` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `notion` | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `web_ical` | ⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| `local_json` | ⭐ | ⭐⭐ | ⭐⭐⭐⭐⭐ |

### Google Drive

| Провайдер | Сложность | Функциональность | Надежность |
|-----------|-----------|------------------|------------|
| `google_api` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| `google_desktop` | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| `local` | ⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🚀 Примеры использования

### Сценарий 1: Корпоративные ограничения
```bash
# Календарь через Notion
CALENDAR_PROVIDER=notion
NOTION_TOKEN=your_token
NOTION_CALENDAR_DATABASE_ID=your_db_id

# Google Drive через Desktop приложение
DRIVE_PROVIDER=google_desktop
GOOGLE_DRIVE_DESKTOP_PATH=/Users/username/Google Drive
```

### Сценарий 2: Офлайн работа
```bash
# Локальный JSON календарь
CALENDAR_PROVIDER=local_json
LOCAL_JSON_FILE=data/calendar/events.json

# Локальная файловая система
DRIVE_PROVIDER=local
LOCAL_DRIVE_ROOT=data/local_drive
```

### Сценарий 3: Публичные календари
```bash
# Веб-календарь iCal
CALENDAR_PROVIDER=web_ical
ICAL_CALENDAR_URL=https://calendar.google.com/ical/your_id/basic.ics

# Google Drive API (если доступен)
DRIVE_PROVIDER=google_api
GOOGLE_DRIVE_CREDENTIALS=creds/client_secret.json
```

## 🔍 Отладка и тестирование

### Проверка конфигурации
```bash
python test_alternative_providers.py
```

### Логи системы
```bash
# Проверьте логи на предмет ошибок
tail -f logs/service_*.log
```

### Тестирование отдельных провайдеров
```python
from src.calendar_alternatives import get_calendar_provider
from src.drive_alternatives import get_drive_provider

# Тест календаря
calendar = get_calendar_provider('notion', 
                                notion_token='your_token',
                                database_id='your_db_id')
events = calendar.get_today_events()
print(f"Событий на сегодня: {len(events)}")

# Тест Google Drive
drive = get_drive_provider('google_desktop', 
                          drive_path='/path/to/drive')
files = drive.list_files()
print(f"Файлов в корне: {len(files)}")
```

## ⚠️ Ограничения и особенности

### Календарь
- **Notion**: Требует правильную структуру базы данных
- **Web iCal/RSS**: Зависит от доступности веб-ресурсов
- **Local**: Требует ручного обновления файлов

### Google Drive
- **Google Desktop**: Требует установки приложения
- **Local**: Нет автоматической синхронизации с облаком

## 🔄 Миграция между провайдерами

### Пошаговая миграция
1. **Настройте новый провайдер** в .env
2. **Протестируйте** работу системы
3. **Переключитесь** на новый провайдер
4. **Проверьте** корректность работы

### Пример миграции с Google API на Notion
```bash
# Было
CALENDAR_PROVIDER=google_api
GOOGLE_CALENDAR_CREDENTIALS=creds/client_secret.json

# Стало
CALENDAR_PROVIDER=notion
NOTION_TOKEN=your_notion_token
NOTION_CALENDAR_DATABASE_ID=your_database_id
```

## 📚 Дополнительные ресурсы

- [Google Calendar iCal интеграция](https://support.google.com/calendar/answer/37100)
- [Notion API документация](https://developers.notion.com/)
- [Google Drive для Desktop](https://www.google.com/drive/download/)
- [iCal формат спецификация](https://tools.ietf.org/html/rfc5545)

## 🆘 Поддержка

При возникновении проблем:

1. **Проверьте логи** системы
2. **Запустите тест** провайдеров
3. **Проверьте конфигурацию** в .env
4. **Убедитесь в доступности** внешних ресурсов

---

**Система альтернативных провайдеров позволяет адаптироваться к любым ограничениям и требованиям среды!** 🎯✨
