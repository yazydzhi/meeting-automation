# 🔄 Система автоматизации встреч для двух аккаунтов

Этот документ описывает новую систему автоматизации встреч, которая позволяет работать с **личным** и **рабочим** аккаунтами одновременно, используя разные провайдеры для обхода корпоративных ограничений.

## 🎯 Проблема и решение

### Проблема
- **Личный аккаунт**: Google API доступен, но нужно отделить от рабочего
- **Рабочий аккаунт**: Google API заблокирован организацией
- **Необходимость**: Работать с обоими аккаунтами одновременно

### Решение
- **Личный аккаунт**: Использует стандартные Google API провайдеры
- **Рабочий аккаунт**: Использует альтернативные провайдеры (iCal, Google Drive Desktop)
- **Универсальный скрипт**: Запускает обработку для обоих аккаунтов

## 📁 Структура файлов

```
meeting_automation/
├── env.personal                    # Конфигурация личного аккаунта
├── env.work                       # Конфигурация рабочего аккаунта
├── meeting_automation_personal.py # Скрипт для личного аккаунта
├── meeting_automation_work.py     # Скрипт для рабочего аккаунта
├── meeting_automation_universal.py # Универсальный скрипт
├── src/
│   ├── calendar_alternatives.py   # Альтернативные провайдеры календаря
│   ├── drive_alternatives.py      # Альтернативные провайдеры Google Drive
│   └── config_manager.py          # Менеджер конфигурации
└── logs/
    ├── personal_automation.log    # Логи личного аккаунта
    ├── work_automation.log        # Логи рабочего аккаунта
    └── universal_automation.log   # Логи универсального скрипта
```

## ⚙️ Конфигурация

### 1. Личный аккаунт (`env.personal`)

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

# Google API настройки
GOOGLE_CALENDAR_CREDENTIALS=creds/client_secret.json
GOOGLE_DRIVE_CREDENTIALS=creds/client_secret.json
```

### 2. Рабочий аккаунт (`env.work`)

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

## 🚀 Использование

### 1. **Только личный аккаунт**

```bash
# Обработка календаря
python meeting_automation_personal.py prepare

# Обработка медиа файлов
python meeting_automation_personal.py media

# Тестирование
python meeting_automation_personal.py test
```

### 2. **Только рабочий аккаунт**

```bash
# Обработка календаря
python meeting_automation_work.py prepare

# Обработка медиа файлов
python meeting_automation_work.py media

# Тестирование
python meeting_automation_work.py test
```

### 3. **Оба аккаунта одновременно**

```bash
# Обработка календаря для обоих
python meeting_automation_universal.py prepare

# Обработка медиа файлов для обоих
python meeting_automation_universal.py media

# Тестирование обоих
python meeting_automation_universal.py test
```

### 4. **Выборочный запуск**

```bash
# Только личный аккаунт
python meeting_automation_universal.py prepare --personal-only

# Только рабочий аккаунт
python meeting_automation_universal.py prepare --work-only
```

## 🔧 Настройка системы

### Шаг 1: Создание конфигурационных файлов

```bash
# Скопируйте примеры (без конфиденциальных данных)
cp env.personal.example env.personal
cp env.work.example env.work

# Отредактируйте под свои нужды
nano env.personal
nano env.work
```

**⚠️ Важно:** Файлы `env.personal` и `env.work` содержат конфиденциальные данные и **НЕ должны** попадать в Git. Они автоматически исключены через `.gitignore`.

### Шаг 2: Настройка провайдеров

#### Для личного аккаунта:
- Убедитесь, что `GOOGLE_CREDENTIALS` указывает на правильный файл
- Проверьте `PERSONAL_CALENDAR_ID` и `PERSONAL_DRIVE_PARENT_ID`
- Установите `CALENDAR_PROVIDER=google_api` и `DRIVE_PROVIDER=google_api`

#### Для рабочего аккаунта:
- Выберите альтернативный провайдер календаря:
  - `web_ical` - для iCal ссылок
  - `notion` - для Notion базы данных
  - `local_json` - для локальных файлов
- Выберите альтернативный провайдер Google Drive:
  - `google_desktop` - для Google Drive Desktop
  - `local` - для локальной файловой системы

### Шаг 3: Получение iCal ссылки для рабочего календаря

1. Откройте Google Calendar
2. Настройки календаря → Интеграция календаря
3. Скопируйте "Ссылку iCal"
4. Вставьте в `ICAL_CALENDAR_URL`

### Шаг 4: Настройка Google Drive Desktop для рабочего аккаунта

1. Скачайте Google Drive для Desktop
2. Войдите в рабочий аккаунт
3. Укажите путь в `GOOGLE_DRIVE_DESKTOP_PATH`

## 📊 Логирование и мониторинг

### Логи по аккаунтам

```bash
# Логи личного аккаунта
tail -f logs/personal_automation.log

# Логи рабочего аккаунта
tail -f logs/work_automation.log

# Логи универсального скрипта
tail -f logs/universal_automation.log
```

### Мониторинг в реальном времени

```bash
# Запуск с выводом в реальном времени
python meeting_automation_universal.py prepare

# Только для рабочего аккаунта
python meeting_automation_work.py prepare
```

## 🔍 Отладка и тестирование

### Тестирование провайдеров

```bash
# Тест личного аккаунта
python meeting_automation_personal.py test

# Тест рабочего аккаунта
python meeting_automation_work.py test

# Тест всех провайдеров
python test_alternative_providers.py
```

### Проверка конфигурации

```bash
# Проверка конфигурации личного аккаунта
python -c "
from src.config_manager import ConfigManager
config = ConfigManager('env.personal')
print(config.get_config_summary())
print('Валидность:', config.validate_config())
"

# Проверка конфигурации рабочего аккаунта
python -c "
from src.config_manager import ConfigManager
config = ConfigManager('env.work')
print(config.get_config_summary())
print('Валидность:', config.validate_config())
"
```

## ⚠️ Особенности и ограничения

### Личный аккаунт
- ✅ Полный доступ к Google API
- ✅ Стандартная обработка медиа файлов
- ✅ Автоматическая синхронизация
- ⚠️ Требует валидные учетные данные Google

### Рабочий аккаунт
- ✅ Обходит корпоративные ограничения
- ✅ Работает с альтернативными провайдерами
- ⚠️ Может требовать ручной настройки
- ⚠️ Некоторые функции могут быть ограничены

## 🚨 Устранение неполадок

### Проблема: Личный аккаунт не работает

```bash
# Проверьте конфигурацию
python meeting_automation_personal.py test

# Проверьте логи
tail -f logs/personal_automation.log

# Убедитесь, что файл учетных данных существует
ls -la creds/client_secret.json
```

### Проблема: Рабочий аккаунт не работает

```bash
# Проверьте конфигурацию
python meeting_automation_work.py test

# Проверьте логи
tail -f logs/work_automation.log

# Проверьте доступность альтернативных ресурсов
curl -I "YOUR_ICAL_URL"
ls -la "YOUR_GOOGLE_DRIVE_PATH"
```

### Проблема: Конфликт между аккаунтами

```bash
# Запустите по отдельности
python meeting_automation_personal.py prepare
python meeting_automation_work.py prepare

# Проверьте разные конфигурации
diff env.personal env.work
```

## 🔄 Миграция с существующей системы

### Шаг 1: Создайте конфигурацию личного аккаунта

```bash
# Скопируйте существующий .env
cp .env env.personal

# Добавьте специфичные для личного аккаунта настройки
echo "CALENDAR_PROVIDER=google_api" >> env.personal
echo "DRIVE_PROVIDER=google_api" >> env.personal
```

### Шаг 2: Создайте конфигурацию рабочего аккаунта

```bash
# Создайте новый файл
cp env.personal env.work

# Измените настройки для рабочего аккаунта
sed -i '' 's/CALENDAR_PROVIDER=google_api/CALENDAR_PROVIDER=web_ical/' env.work
sed -i '' 's/DRIVE_PROVIDER=google_api/DRIVE_PROVIDER=google_desktop/' env.work
```

### Шаг 3: Протестируйте оба аккаунта

```bash
# Тест личного
python meeting_automation_personal.py test

# Тест рабочего
python meeting_automation_work.py test

# Тест обоих
python meeting_automation_universal.py test
```

## 📈 Расширение функциональности

### Добавление новых провайдеров

1. Создайте новый класс в `src/calendar_alternatives.py` или `src/drive_alternatives.py`
2. Добавьте поддержку в `ConfigManager`
3. Обновите конфигурационные файлы
4. Протестируйте новый провайдер

### Добавление новых аккаунтов

1. Создайте `env.account_name`
2. Создайте `meeting_automation_account_name.py`
3. Добавьте поддержку в универсальный скрипт
4. Обновите документацию

## 🔒 Безопасность и конфиденциальность

### Конфигурационные файлы
- **`env.personal`** и **`env.work`** содержат конфиденциальные данные (токены, ID, пути)
- Эти файлы **автоматически исключены** из Git через `.gitignore`
- **Никогда не коммитьте** эти файлы в репозиторий

### Примеры конфигураций
- **`env.personal.example`** и **`env.work.example`** - безопасные примеры без реальных данных
- Пользователи копируют их и заполняют своими данными
- Примеры можно безопасно хранить в Git

### Проверка безопасности
```bash
# Убедитесь, что конфиденциальные файлы не отслеживаются
git status

# Проверьте, что они игнорируются
git check-ignore env.personal env.work

# Проверьте, что примеры НЕ игнорируются
git check-ignore env.personal.example env.work.example
```

## 📚 Дополнительные ресурсы

- [ALTERNATIVE_PROVIDERS_README.md](ALTERNATIVE_PROVIDERS_README.md) - Подробное описание альтернативных провайдеров
- [SERVICE_README.md](SERVICE_README.md) - Настройка системы как сервиса
- [README.md](README.md) - Основная документация проекта

## 🆘 Поддержка

При возникновении проблем:

1. **Проверьте логи** соответствующего аккаунта
2. **Запустите тест** для диагностики
3. **Проверьте конфигурацию** в env файлах
4. **Убедитесь в доступности** внешних ресурсов
5. **Проверьте права доступа** к файлам и папкам

---

**Система с двумя аккаунтами позволяет эффективно работать с личными и рабочими данными, обходя любые корпоративные ограничения!** 🎯✨
