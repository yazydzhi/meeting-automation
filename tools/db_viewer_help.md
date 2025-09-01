# Консольный DB Viewer

Удобный инструмент для просмотра данных в SQLite базе состояния системы.

## Использование

```bash
# Основные команды
python tools/db_viewer.py <команда> [опции]

# Или с указанием базы данных
python tools/db_viewer.py --db data/system_state.db <команда>
```

## Доступные команды

### 📋 `tables` - Показать все таблицы
```bash
python tools/db_viewer.py tables
```

### 📊 `stats` - Общая статистика
```bash
python tools/db_viewer.py stats
```
Показывает:
- Общее количество циклов, событий, медиа файлов
- Статистику по аккаунтам
- Информацию о последнем цикле

### 🔄 `state` - Состояние системы
```bash
python tools/db_viewer.py state --limit 10
```
Показывает последние состояния системы с метриками и статусами.

### 📅 `events` - Обработанные события
```bash
# Все события
python tools/db_viewer.py events --limit 20

# Только рабочие события
python tools/db_viewer.py events --account work --limit 10

# Только личные события
python tools/db_viewer.py events --account personal --limit 10
```

### 🎬 `media` - Обработанные медиа файлы
```bash
python tools/db_viewer.py media --limit 20
```

### 🎤 `transcriptions` - Обработанные транскрипции
```bash
python tools/db_viewer.py transcriptions --limit 20
```

### 📝 `notion` - Синхронизация с Notion
```bash
python tools/db_viewer.py notion --limit 20
```

### 🔍 `search` - Поиск событий
```bash
# Поиск по названию
python tools/db_viewer.py search "встреча" --limit 10

# Поиск по части названия
python tools/db_viewer.py search "Эл" --limit 5
```

### 🔍 `raw` - Сырое состояние цикла
```bash
python tools/db_viewer.py raw 1
```
Показывает полное JSON состояние для указанного цикла.

## Примеры использования

### Мониторинг системы
```bash
# Быстрая проверка статистики
python tools/db_viewer.py stats

# Последние состояния
python tools/db_viewer.py state --limit 5
```

### Отладка событий
```bash
# Все события за последнее время
python tools/db_viewer.py events --limit 50

# Поиск конкретного события
python tools/db_viewer.py search "ретроспектива"
```

### Анализ производительности
```bash
# Время выполнения циклов
python tools/db_viewer.py state --limit 20 | grep "Время выполнения"

# Ошибки в циклах
python tools/db_viewer.py state --limit 20 | grep "Ошибки:"
```

## Создание алиасов

Для удобства можно создать алиасы в `.bashrc` или `.zshrc`:

```bash
# Алиас для быстрого доступа
alias dbview='python /Users/azg/repository/meeting_automation/tools/db_viewer.py'

# Использование
dbview stats
dbview events --limit 10
dbview search "встреча"
```

## Структура базы данных

### `system_state` - Состояние системы
- `cycle_id` - ID цикла обработки
- `timestamp` - Время выполнения
- `*_processed` - Количество обработанных элементов
- `*_status` - Статусы обработки
- `execution_time` - Время выполнения цикла
- `raw_state` - Полное JSON состояние

### `processed_events` - Обработанные события
- `event_id` - Уникальный ID события
- `account_type` - Тип аккаунта (personal/work)
- `event_title` - Название события
- `processed_at` - Время обработки

### `processed_media` - Обработанные медиа файлы
- `file_path` - Путь к файлу
- `file_hash` - Хеш файла
- `status` - Статус обработки
- `processed_at` - Время обработки

### `processed_transcriptions` - Обработанные транскрипции
- `file_path` - Путь к файлу
- `status` - Статус обработки
- `processed_at` - Время обработки

### `notion_sync` - Синхронизация с Notion
- `page_id` - ID страницы в Notion
- `event_id` - ID связанного события
- `status` - Статус синхронизации
- `last_sync` - Время последней синхронизации
