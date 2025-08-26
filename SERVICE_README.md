# 🚀 Сервис автоматизации встреч

## 📋 Обзор

Сервис автоматизации встреч работает в фоновом режиме и автоматически обрабатывает календари и медиа файлы для личного и рабочего аккаунтов.

## 🔧 Установка и настройка

### 1. Подготовка окружения

```bash
# Активация виртуального окружения
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Конфигурация

Убедитесь, что у вас настроен файл конфигурации `.env`. Пример конфигурации можно найти в файле `.env.example`.

### 3. Установка сервиса

```bash
# Загрузка сервиса в launchd
launchctl load launchd/com.yourname.meeting-automation.plist
```

## 🎮 Управление сервисом

### Использование скрипта управления

```bash
# Показать статус
./scripts/service_control.sh status

# Запустить сервис
./scripts/service_control.sh start

# Остановить сервис
./scripts/service_control.sh stop

# Перезапустить сервис
./scripts/service_control.sh restart

# Показать логи
./scripts/service_control.sh logs [количество_строк]

# Показать ошибки
./scripts/service_control.sh errors [количество_строк]

# Показать справку
./scripts/service_control.sh help
```

### Прямое управление через launchctl

```bash
# Загрузка сервиса
launchctl load launchd/com.yourname.meeting-automation.plist

# Выгрузка сервиса
launchctl unload launchd/com.yourname.meeting-automation.plist

# Проверка статуса
launchctl list | grep meeting
```

## ⚙️ Конфигурация сервиса

### Параметры plist файла

- **Интервал проверки**: 300 секунд (5 минут)
- **Интервал медиа**: 1800 секунд (30 минут)
- **Автозапуск**: Включен (`RunAtLoad: true`)
- **Постоянная работа**: Включена (`KeepAlive: true`)

### Изменение параметров

Для изменения интервалов отредактируйте файл `launchd/com.yourname.meeting-automation.plist`:

```xml
<key>ProgramArguments</key>
<array>
    <string>/Users/yourname/repository/meeting_automation/venv/bin/python</string>
    <string>/Users/yourname/repository/meeting_automation/src/service_manager.py</string>
    <string>--interval</string>
    <string>300</string>  <!-- Интервал проверки в секундах -->
    <string>--media-interval</string>
    <string>1800</string> <!-- Интервал медиа обработки в секундах -->
</array>
```

## 📊 Мониторинг
## 🔧 Последние исправления

### ✅ Устраненные критические ошибки
- **Ошибка `_create_cycle_state`** - исправлена, сервис запускается стабильно
- **Ошибка `get_openai_config`** - исправлена, генерация саммари работает
- **Ошибка календаря** - исправлена проблема с пустым URL
- **Стандартизация файлов статуса** - единообразные названия

### 🆕 Новые возможности
- **Автоматическая проверка статуса** - скрипт `check_folders.py`
- **Интеграция с мониторингом** - функция `check_and_update_status`
- **Улучшенная обработка ошибок** - детальное логирование


### Логи

- **Основной лог**: `logs/service.log`
- **Лог ошибок**: `logs/service_error.log`

### Просмотр логов в реальном времени

```bash
# Основной лог
tail -f logs/service.log

# Лог ошибок
tail -f logs/service_error.log
```

### Проверка процессов

```bash
# Поиск процессов сервиса
ps aux | grep "service_manager.py" | grep -v grep
```

## 🔍 Диагностика

### Проверка статуса

```bash
./scripts/service_control.sh status
```

### Тестирование сервиса

```bash
# Запуск в тестовом режиме с короткими интервалами
python src/service_manager.py --interval 10 --media-interval 30
```

### Проверка конфигурации

```bash
# Проверка файлов конфигурации
ls -la .env*

# Проверка переменных окружения
grep -E "^[A-Z]" .env | sort
```

## 🚨 Устранение неполадок

### Сервис не запускается

1. Проверьте логи:
   ```bash
   ./scripts/service_control.sh errors
   ```

2. Проверьте конфигурацию:
   ```bash
   python meeting_automation_universal.py test --config-only
   ```

3. Проверьте зависимости:
   ```bash
   source venv/bin/activate
   pip list | grep -E "(dotenv|requests)"
   ```

### Сервис не обрабатывает аккаунты

1. Проверьте файлы конфигурации:
   ```bash
   ls -la .env*
   ```

2. Проверьте переменные окружения:
   ```bash
   grep -E "^[A-Z]" .env | sort
   ```

3. Запустите тесты вручную:
   ```bash
   python meeting_automation_personal.py prepare
   python meeting_automation_work.py prepare
   ```

### Высокое потребление ресурсов

1. Увеличьте интервалы в plist файле
2. Проверьте логи на наличие ошибок
3. Перезапустите сервис:
   ```bash
   ./scripts/service_control.sh restart
   ```

## 📁 Структура файлов

```
meeting_automation/
├── launchd/
│   └── com.yourname.meeting-automation.plist  # Конфигурация launchd
├── src/
│   └── service_manager.py                      # Основной сервис
├── scripts/
│   └── service_control.sh                      # Скрипт управления
├── logs/
│   ├── service.log                             # Основной лог
│   └── service_error.log                       # Лог ошибок
└── .env*                                       # Конфигурационные файлы
```

## 🔄 Автоматизация

### Добавление в автозапуск

Сервис автоматически запускается при загрузке системы благодаря `RunAtLoad: true` в plist файле.

### Планировщик задач

Для дополнительной автоматизации можно использовать cron:

```bash
# Редактирование crontab
crontab -e

# Добавить строку для ежедневного перезапуска в 6:00
0 6 * * * cd /Users/yourname/repository/meeting_automation && ./scripts/service_control.sh restart
```

## 📚 Дополнительные ресурсы

- [README.md](README.md) - Основная документация проекта
- [launchd.plist](https://www.launchd.info/) - Документация по launchd
- [macOS Services](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html) - Создание сервисов macOS

## 🆘 Поддержка

При возникновении проблем:

1. Проверьте логи: `./scripts/service_control.sh logs 50`
2. Проверьте статус: `./scripts/service_control.sh status`
3. Перезапустите сервис: `./scripts/service_control.sh restart`
4. Запустите тесты: `python meeting_automation_universal.py test --config-only`

---

**🎯 Сервис автоматизации встреч готов к работе!**
