# 🎤 Обработка MP3 файлов из папок

## Обзор

Скрипт `tools/process_mp3_folders.py` автоматически обрабатывает все MP3 файлы в указанных папках с помощью Whisper API и сохраняет результаты транскрипции в тех же папках в различных форматах.

## 🚀 Возможности

- **Автоматический поиск** MP3 файлов в папках
- **Рекурсивный поиск** в подпапках (опционально)
- **Множественные форматы** вывода: TXT, MD, CSV, JSON, SRT
- **Сохранение в исходных папках** - транскрипты создаются рядом с MP3 файлами
- **Умная обработка** - пропускает уже обработанные файлы
- **Принудительная обработка** - возможность перезаписать существующие транскрипты
- **Подробная статистика** процесса обработки

## 📋 Требования

### Зависимости
```bash
pip install openai pydub
```

### Конфигурация
В `.env` файле должны быть настроены:
```bash
# OpenAI API
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ORGANIZATION=your_openai_org_id_here

# Whisper настройки
WHISPER_MODEL=base
WHISPER_LANGUAGE=ru
WHISPER_TASK=transcribe
```

## 🛠️ Использование

### 1. Python скрипт

#### Базовое использование
```bash
# Обработать одну папку в формате TXT
python tools/process_mp3_folders.py /path/to/folder

# Обработать несколько папок
python tools/process_mp3_folders.py /path/to/folder1 /path/to/folder2

# Указать формат вывода
python tools/process_mp3_folders.py /path/to/folder --output md
```

#### Все параметры
```bash
python tools/process_mp3_folders.py [папки] [опции]

Опции:
  --output {txt,md,csv,json,srt}  Формат вывода (по умолчанию: txt)
  --recursive                      Искать MP3 файлы рекурсивно (по умолчанию: Да)
  --no-recursive                   Искать MP3 файлы только в указанных папках
  --force                          Принудительная обработка всех файлов
  --config CONFIG                  Путь к конфигурационному файлу
```

### 2. Bash скрипт (быстрый запуск)

#### Установка
```bash
chmod +x tools/quick_mp3_process.sh
```

#### Использование
```bash
# Обработать в формате TXT (по умолчанию)
./tools/quick_mp3_process.sh /path/to/folder

# Обработать в формате Markdown
./tools/quick_mp3_process.sh /path/to/folder md

# Обработать в формате CSV
./tools/quick_mp3_process.sh /path/to/folder csv
```

## 📁 Форматы вывода

### 1. TXT (по умолчанию)
```
Транскрипция аудио файла: meeting.mp3
Длительность: 3600000ms
Количество сегментов: 45
Количество участников: 3
==================================================

Участник 1:
[0-3000ms] Добро пожаловать на встречу
[5000-8000ms] Сегодня мы обсудим важные вопросы

Участник 2:
[10000-13000ms] Спасибо за приглашение
```

### 2. Markdown (MD)
```markdown
# Транскрипция: meeting.mp3

**Файл:** meeting.mp3
**Размер:** 15728640 байт
**Длительность:** 3600000ms
**Сегментов:** 45
**Участников:** 3
**Модель Whisper:** base
**Язык:** ru

---

## Участник 1

**Общая длительность:** 1200000ms

**[0.0s - 3.0s]** Добро пожаловать на встречу

**[5.0s - 8.0s]** Сегодня мы обсудим важные вопросы
```

### 3. CSV
```csv
speaker_id,start_time,end_time,duration,text
"Участник 1",0.0,3.0,3.0,"Добро пожаловать на встречу"
"Участник 1",5.0,8.0,3.0,"Сегодня мы обсудим важные вопросы"
"Участник 2",10.0,13.0,3.0,"Спасибо за приглашение"
```

### 4. JSON
```json
{
  "file_path": "meeting.mp3",
  "duration": 3600000,
  "segments_count": 45,
  "speakers_count": 3,
  "transcription": [
    {
      "speaker_id": "Участник 1",
      "segments": [
        {
          "text": "Добро пожаловать на встречу",
          "start_time": 0,
          "end_time": 3000,
          "duration": 3000
        }
      ],
      "total_duration": 1200000
    }
  ]
}
```

### 5. SRT (субтитры)
```
1
00:00:00,000 --> 00:00:03,000
Участник 1: Добро пожаловать на встречу

2
00:00:05,000 --> 00:00:08,000
Участник 1: Сегодня мы обсудим важные вопросы
```

## 🎯 Примеры использования

### Обработка папки с встречами
```bash
# Обработать все MP3 файлы в папке встреч
python tools/process_mp3_folders.py ~/Downloads/meetings --output md

# Результат: в папке ~/Downloads/meetings появятся файлы:
# - meeting1_transcript.md
# - meeting2_transcript.md
# - interview_transcript.md
```

### Обработка нескольких папок
```bash
# Обработать папки для работы и личных встреч
python tools/process_mp3_folders.py ~/Work/meetings ~/Personal/recordings --output csv
```

### Принудительная обработка
```bash
# Перезаписать все существующие транскрипты
python tools/process_mp3_folders.py /path/to/folder --output txt --force
```

### Только текущая папка (без рекурсии)
```bash
# Обработать только MP3 файлы в указанной папке
python tools/process_mp3_folders.py /path/to/folder --no-recursive --output json
```

## 📊 Статистика обработки

После завершения скрипт выводит подробную статистику:

```
============================================================
📊 ИТОГОВАЯ СТАТИСТИКА
============================================================
📁 Всего папок: 2
🎵 Всего MP3 файлов: 15
✅ Успешно обработано: 12
⏭️  Пропущено: 2
❌ Ошибок: 1
⏱️  Среднее время обработки: 45.2с
⏱️  Общее время обработки: 542.4с
🧹 Временные файлы очищены
🏁 Обработка завершена!
```

## 🔧 Настройка

### Конфигурационный файл
Можно указать отдельный конфигурационный файл:
```bash
python tools/process_mp3_folders.py /path/to/folder --config env.work
```

### Переменные окружения
Основные настройки в `.env`:
```bash
# Whisper модель
WHISPER_MODEL=base          # tiny, base, small, medium

# Язык
WHISPER_LANGUAGE=ru         # ru, en, auto

# Задача
WHISPER_TASK=transcribe     # transcribe, translate

# Логирование
LOG_LEVEL=INFO
LOG_FILE=logs/mp3_processing.log
```

## 🚨 Обработка ошибок

### Типичные ошибки

1. **Отсутствует OpenAI API ключ**
   ```
   ValueError: OPENAI_API_KEY не найден в конфигурации
   ```

2. **Папка не найдена**
   ```
   ❌ Папка не найдена: /path/to/nonexistent/folder
   ```

3. **MP3 файлы не найдены**
   ```
   ℹ️  MP3 файлы не найдены
   ```

4. **Ошибка транскрипции**
   ```
   ❌ Транскрипция не удалась
   ```

### Рекомендации

- Убедитесь в наличии всех зависимостей
- Проверьте валидность OpenAI API ключа
- Убедитесь в существовании указанных папок
- Проверьте наличие MP3 файлов в папках

## 📈 Производительность

### Время обработки (примерно)

| Длительность | Модель | Время обработки |
|--------------|--------|-----------------|
| 5 минут      | base   | 30-60 секунд    |
| 15 минут     | base   | 2-4 минуты      |
| 1 час        | base   | 8-15 минут      |

### Факторы влияния
- **Качество интернета** - для API запросов
- **Размер аудио файла** - для загрузки
- **Модель Whisper** - для точности и скорости
- **Количество файлов** - для пакетной обработки

## 🔄 Автоматизация

### Cron задача (Linux/macOS)
```bash
# Обрабатывать новые MP3 файлы каждый час
0 * * * * cd /path/to/project && python tools/process_mp3_folders.py /path/to/meetings --output md
```

### Systemd сервис (Linux)
Создайте сервис для автоматической обработки:
```ini
[Unit]
Description=MP3 Transcription Service
After=network.target

[Service]
Type=oneshot
User=your_user
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 tools/process_mp3_folders.py /path/to/meetings --output md
```

### Интеграция с основными скриптами
Используйте команду `audio` в основных скриптах:
```bash
# Рабочий аккаунт
python meeting_automation_work.py audio --folders 5 --output md

# Личный аккаунт
python meeting_automation_personal.py audio --folders 5 --output csv

# Универсальный запуск
python meeting_automation_universal.py audio --output txt --personal-only
```

## 🧪 Тестирование

### Тестовая папка
```bash
# Создать тестовую папку
mkdir test_mp3_folder
echo "test" > test_mp3_folder/sample.mp3

# Протестировать обработку
python tools/process_mp3_folders.py test_mp3_folder --output md
```

### Проверка результатов
```bash
# Посмотреть созданные файлы
ls -la test_mp3_folder/

# Проверить содержимое транскрипта
cat test_mp3_folder/sample_transcript.md
```

## 📞 Поддержка

### Полезные команды

```bash
# Проверка зависимостей
pip list | grep -E "(openai|pydub)"

# Проверка конфигурации
python tools/process_mp3_folders.py --help

# Проверка логов
tail -f logs/mp3_processing.log

# Очистка временных файлов
rm -rf data/temp_audio/*
```

### Полезные ссылки
- [OpenAI Whisper API](https://platform.openai.com/docs/guides/speech-to-text)
- [PyDub Documentation](https://github.com/jiaaro/pydub)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)

---

**Примечание**: Скрипт автоматически создает логи в `logs/mp3_processing.log` для отслеживания процесса обработки и диагностики проблем.
