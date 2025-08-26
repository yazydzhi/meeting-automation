# 📊 Руководство по мониторингу папок встреч

## 🚀 Быстрый старт

```bash
# Переходим в директорию проекта
cd /Users/azg/repository/meeting_automation

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем мониторинг
python scripts/folder_status_monitor.py
```

## 📋 Основные команды

### 1. Базовый мониторинг
```bash
python scripts/folder_status_monitor.py
```
Показывает текущее состояние всех папок встреч в консоли.

### 2. Сохранение отчета
```bash
python scripts/folder_status_monitor.py --save
```
Сохраняет отчет в файл с временной меткой: `folder_status_report_YYYYMMDD_HHMMSS.txt`

### 3. Указание пути для сохранения
```bash
python scripts/folder_status_monitor.py --save --output my_report.txt
```
Сохраняет отчет в указанный файл.

### 4. Отправка в Telegram
```bash
python scripts/folder_status_monitor.py --telegram
```
Отправляет отчет в настроенный Telegram бот.

### 5. Комбинированный режим
```bash
python scripts/folder_status_monitor.py --save --telegram
```
Сохраняет отчет в файл И отправляет в Telegram.

## 🔍 Что анализирует скрипт

### 📂 Структура папок
- **Личный аккаунт**: `/Users/azg/Downloads/01 - yazydzhi@gmail.com/`
- **Рабочий аккаунт**: `/Users/azg/Downloads/02 - v.yazydzhi@cian.ru/`

### 🔄 Этапы обработки
1. **🎬 Сжатие видео** - создание `_compressed.mp4`
2. **🎵 Извлечение аудио** - создание `_compressed.mp3`
3. **📝 Транскрипция** - создание `_transcript.txt`
4. **📋 Саммари** - создание `_summary.txt`
5. **🔗 Notion** - создание `_notion_data.json`

### 📊 Статусы папок
- **✅ completed** - все этапы завершены (100%)
- **🟡 near_completion** - почти завершено (75-99%)
- **🔄 in_progress** - в процессе (50-74%)
- **🟠 started** - начато (25-49%)
- **❌ not_started** - не начато (0-24%)

## 📅 Интеграции

### Google Calendar
- Ищет события по дате из названия папки
- Связывает папки с календарными событиями
- Показывает время и участников встречи

### Notion
- Ищет записи в базе данных по ключевым словам
- Показывает статус и ссылки на записи
- Отслеживает синхронизацию данных

## 🛠️ Устранение неполадок

### Ошибка "CalendarEvent object has no attribute 'get'"
Это нормально - скрипт корректно обрабатывает объекты календаря.

### Ошибка "NotionAPI.__init__() missing 1 required positional argument"
Проверьте настройки Notion в `.env` файле.

### Ошибка "Ошибка загрузки календаря: 404"
Проверьте URL календаря в настройках аккаунта.

## 🔄 Автоматизация

### Cron (macOS/Linux)
```bash
# Каждые 5 минут
*/5 * * * * cd /Users/azg/repository/meeting_automation && source venv/bin/activate && python scripts/folder_status_monitor.py --save --telegram

# Каждый час
0 * * * * cd /Users/azg/repository/meeting_automation && source venv/bin/activate && python scripts/folder_status_monitor.py --save
```

### launchctl (macOS)
Создайте plist файл для автоматического запуска:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.yazydzhi.folder-monitoring</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Users/azg/repository/meeting_automation/venv/bin/python</string>
        <string>/Users/azg/repository/meeting_automation/scripts/folder_status_monitor.py</string>
        <string>--save</string>
        <string>--telegram</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>/Users/azg/repository/meeting_automation</string>
    
    <key>StartInterval</key>
    <integer>300</integer>
    
    <key>RunAtLoad</key>
    <true/>
</dict>
</plist>
```

## 📱 Telegram уведомления

### Настройка бота
1. Создайте бота через @BotFather
2. Получите `bot_token`
3. Добавьте в `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Формат сообщений
- Использует Markdown для форматирования
- Эмодзи для наглядности
- Структурированная информация
- Ссылки на файлы и записи

## 📈 Анализ результатов

### Ключевые метрики
- **Общее количество папок** - сколько встреч обрабатывается
- **Процент завершения** - общий прогресс по системе
- **Статус по этапам** - где возникают задержки
- **Интеграции** - связь с внешними системами

### Типичные сценарии
1. **Новые встречи** - статус "not_started", 0% прогресса
2. **В процессе** - статус "in_progress", 40-60% прогресса
3. **Почти завершено** - статус "near_completion", 75-99% прогресса
4. **Завершено** - статус "completed", 100% прогресса

## 🔧 Кастомизация

### Изменение интервалов
Отредактируйте скрипт для изменения частоты проверок.

### Добавление новых этапов
Расширьте логику в методе `_analyze_processing_status()`.

### Изменение формата отчета
Модифицируйте метод `generate_report()`.

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в консоли
2. Убедитесь в корректности настроек `.env`
3. Проверьте доступность внешних сервисов
4. Обратитесь к основному README.md
