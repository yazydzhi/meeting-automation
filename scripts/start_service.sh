#!/bin/bash

# Скрипт запуска сервиса meeting automation
# Путь к проекту
PROJECT_DIR="/Users/azg/repository/meeting_automation"
LOG_FILE="$PROJECT_DIR/logs/service.log"
PID_FILE="$PROJECT_DIR/data/service.pid"

# Переходим в директорию проекта
cd "$PROJECT_DIR"

# Проверяем, не запущен ли уже сервис
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "$(date): Сервис уже запущен (PID: $PID)" >> "$LOG_FILE"
        exit 0
    else
        echo "$(date): Удаляю устаревший PID файл" >> "$LOG_FILE"
        rm -f "$PID_FILE"
    fi
fi

# Активируем виртуальное окружение
source venv/bin/activate

# Запускаем сервис
echo "$(date): Запуск сервиса meeting automation" >> "$LOG_FILE"
python src/service_manager.py --config .env --log-level INFO --interval 300 --media-interval 1800 >> "$LOG_FILE" 2>&1 &

# Сохраняем PID
echo $! > "$PID_FILE"
echo "$(date): Сервис запущен (PID: $!)" >> "$LOG_FILE"
