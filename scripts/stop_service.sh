#!/bin/bash

# Скрипт остановки сервиса meeting automation
PROJECT_DIR="/Users/azg/repository/meeting_automation"
LOG_FILE="$PROJECT_DIR/logs/service.log"
PID_FILE="$PROJECT_DIR/data/service.pid"

# Переходим в директорию проекта
cd "$PROJECT_DIR"

# Проверяем PID файл
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "$(date): Останавливаю сервис (PID: $PID)" >> "$LOG_FILE"
    
    # Останавливаем процесс
    if kill $PID 2>/dev/null; then
        echo "$(date): Сервис остановлен" >> "$LOG_FILE"
    else
        echo "$(date): Процесс не найден, удаляю PID файл" >> "$LOG_FILE"
    fi
    
    # Удаляем PID файл
    rm -f "$PID_FILE"
else
    echo "$(date): PID файл не найден, останавливаю все процессы service_manager" >> "$LOG_FILE"
    pkill -f service_manager
fi

echo "$(date): Остановка сервиса завершена" >> "$LOG_FILE"
