# 📋 Управление логами системы автоматизации встреч

## 🔍 Текущее состояние

Система логирования была оптимизирована для устранения дублирования и улучшения управления файлами.

### 📁 Структура логов

**Основные лог файлы:**
- `logs/service.log` - основной лог сервиса (с ротацией)
- `logs/meeting_automation_universal.log` - лог универсального скрипта (с ротацией)
- `logs/audio_processing.log` - лог обработки аудио (с ротацией)

**Удаленные дублирующие файлы:**
- ~~`service_error.log`~~ - дублировал service.log
- ~~`universal_automation.log`~~ - дублировал meeting_automation_universal.log

## ⚙️ Настройки в .env

```bash
# ========================================
# НАСТРОЙКИ ЛОГИРОВАНИЯ
# ========================================

# Логирование
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30
LOG_MAX_SIZE_MB=100
LOG_BACKUP_COUNT=5
LOG_ROTATION_ENABLED=true
```

### Параметры:

- **`LOG_LEVEL`** - уровень логирования (INFO, DEBUG, WARNING, ERROR)
- **`LOG_RETENTION_DAYS`** - количество дней хранения логов (по умолчанию: 30)
- **`LOG_MAX_SIZE_MB`** - максимальный размер лог файла в MB (по умолчанию: 100)
- **`LOG_BACKUP_COUNT`** - количество резервных копий при ротации (по умолчанию: 5)
- **`LOG_ROTATION_ENABLED`** - включение/отключение ротации (по умолчанию: true)

## 🛠️ Инструменты управления

### 1. Анализ логов

```bash
# Анализ текущего состояния
python scripts/log_manager.py --action analyze

# Анализ с переопределенными параметрами
python scripts/log_manager.py --action analyze --retention-days 15 --max-size-mb 50
```

### 2. Ротация логов

```bash
# Ротация больших файлов
python scripts/log_manager.py --action rotate

# Ротация с настройками
python scripts/log_manager.py --action rotate --max-size-mb 50
```

### 3. Очистка старых логов

```bash
# Очистка по времени хранения
python scripts/log_manager.py --action cleanup

# Очистка с настройками
python scripts/log_manager.py --action cleanup --retention-days 15
```

### 4. Консолидация логов

```bash
# Удаление дублирующих файлов
python scripts/log_manager.py --action consolidate
```

### 5. Полная оптимизация

```bash
# Выполнение всех операций
python scripts/log_manager.py --action optimize
```

## 🔄 Автоматическая очистка

### Cron задача (ежедневно в 2:00)

```bash
# Добавить в crontab
0 2 * * * cd /path/to/meeting_automation && /usr/bin/python3 scripts/cron_log_cleanup.py >> logs/cron_cleanup.log 2>&1
```

### Ручной запуск

```bash
# Запуск автоматической очистки
python scripts/cron_log_cleanup.py
```

## 📊 Мониторинг

### Проверка размера логов

```bash
# Общий размер всех логов
du -sh logs/

# Размер отдельных файлов
ls -lah logs/*.log
```

### Проверка ротации

```bash
# Поиск резервных копий
ls -lah logs/*.log.*

# Проверка количества файлов
ls logs/*.log | wc -l
```

## 🚨 Устранение проблем

### Логи не ротируются

1. Проверить настройку `LOG_ROTATION_ENABLED=true` в .env
2. Убедиться, что размер файла превышает `LOG_MAX_SIZE_MB`
3. Проверить права на запись в папку logs/

### Логи не очищаются

1. Проверить настройку `LOG_RETENTION_DAYS` в .env
2. Убедиться, что cron задача настроена корректно
3. Проверить права на удаление файлов

### Ошибки импорта

1. Убедиться, что скрипт запускается из корневой директории проекта
2. Проверить, что виртуальное окружение активировано
3. Убедиться, что все зависимости установлены

## 📈 Рекомендации

### Для разработки
- Установить `LOG_LEVEL=DEBUG` для детального логирования
- Уменьшить `LOG_RETENTION_DAYS=7` для экономии места
- Установить `LOG_MAX_SIZE_MB=10` для частой ротации

### Для продакшена
- Установить `LOG_LEVEL=INFO` для оптимального объема
- Установить `LOG_RETENTION_DAYS=90` для долгосрочного хранения
- Установить `LOG_MAX_SIZE_MB=100` для редкой ротации

### Для мониторинга
- Настроить cron задачу для ежедневной очистки
- Регулярно проверять размер логов
- Мониторить количество резервных копий

## 🔗 Связанные файлы

- `scripts/log_manager.py` - основной менеджер логов
- `scripts/cron_log_cleanup.py` - скрипт для cron
- `src/service_manager.py` - настройки логирования сервиса
- `meeting_automation_universal.py` - настройки логирования универсального скрипта
- `tools/process_mp3_folders.py` - настройки логирования обработки MP3
- `src/audio_processor.py` - настройки логирования аудио процессора
