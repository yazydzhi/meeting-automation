#!/bin/bash

# Скрипт для управления сервисом автоматизации встреч
# Поддерживает команды: start, stop, restart, status, logs

SERVICE_NAME="com.yazydzhi.meeting-automation"
PLIST_PATH="launchd/${SERVICE_NAME}.plist"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветного текста
print_status() {
    local status=$1
    local message=$2
    
    case $status in
        "success")
            echo -e "${GREEN}✅ $message${NC}"
            ;;
        "error")
            echo -e "${RED}❌ $message${NC}"
            ;;
        "warning")
            echo -e "${YELLOW}⚠️  $message${NC}"
            ;;
        "info")
            echo -e "${BLUE}ℹ️  $message${NC}"
            ;;
    esac
}

# Функция для проверки статуса сервиса
check_service_status() {
    if launchctl list | grep -q "$SERVICE_NAME"; then
        return 0  # Сервис запущен
    else
        return 1  # Сервис остановлен
    fi
}

# Функция для запуска сервиса
start_service() {
    print_status "info" "Запуск сервиса автоматизации встреч..."
    
    if check_service_status; then
        print_status "warning" "Сервис уже запущен"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    
    if [ ! -f "$PLIST_PATH" ]; then
        print_status "error" "Файл конфигурации не найден: $PLIST_PATH"
        return 1
    fi
    
    # Создаем директорию для логов
    mkdir -p logs
    
    # Загружаем сервис
    if launchctl load "$PLIST_PATH"; then
        print_status "success" "Сервис успешно запущен"
        
        # Ждем немного и проверяем статус
        sleep 2
        if check_service_status; then
            print_status "success" "Сервис работает и обрабатывает аккаунты"
        else
            print_status "error" "Сервис не запустился корректно"
            return 1
        fi
    else
        print_status "error" "Ошибка запуска сервиса"
        return 1
    fi
}

# Функция для остановки сервиса
stop_service() {
    print_status "info" "Остановка сервиса автоматизации встреч..."
    
    if ! check_service_status; then
        print_status "warning" "Сервис уже остановлен"
        return 0
    fi
    
    cd "$PROJECT_DIR"
    
    # Останавливаем сервис
    if launchctl unload "$PLIST_PATH"; then
        print_status "success" "Сервис успешно остановлен"
    else
        print_status "error" "Ошибка остановки сервиса"
        return 1
    fi
}

# Функция для перезапуска сервиса
restart_service() {
    print_status "info" "Перезапуск сервиса автоматизации встреч..."
    
    stop_service
    if [ $? -eq 0 ]; then
        sleep 2
        start_service
    else
        print_status "error" "Не удалось остановить сервис для перезапуска"
        return 1
    fi
}

# Функция для проверки статуса
show_status() {
    print_status "info" "Статус сервиса автоматизации встреч:"
    
    if check_service_status; then
        print_status "success" "Сервис запущен и работает"
        
        # Показываем информацию о процессе
        echo ""
        print_status "info" "Информация о процессе:"
        ps aux | grep "service_manager.py" | grep -v grep | while read line; do
            echo "   $line"
        done
        
        # Показываем последние логи
        echo ""
        print_status "info" "Последние записи в логе:"
        if [ -f "logs/service.log" ]; then
            tail -5 logs/service.log | sed 's/^/   /'
        else
            echo "   Лог файл не найден"
        fi
        
    else
        print_status "error" "Сервис остановлен"
    fi
}

# Функция для показа логов
show_logs() {
    local lines=${1:-20}
    
    print_status "info" "Показ последних $lines строк лога:"
    
    if [ -f "logs/service.log" ]; then
        tail -n "$lines" logs/service.log
    else
        print_status "error" "Лог файл не найден: logs/service.log"
        return 1
    fi
}

# Функция для показа ошибок
show_errors() {
    local lines=${1:-20}
    
    print_status "info" "Показ последних $lines строк лога ошибок:"
    
    if [ -f "logs/service_error.log" ]; then
        tail -n "$lines" logs/service_error.log
    else
        print_status "error" "Лог файл ошибок не найден: logs/service_error.log"
        return 1
    fi
}

# Функция для показа помощи
show_help() {
    echo "Использование: $0 {start|stop|restart|status|logs|errors|help}"
    echo ""
    echo "Команды:"
    echo "  start     - Запустить сервис"
    echo "  stop      - Остановить сервис"
    echo "  restart   - Перезапустить сервис"
    echo "  status    - Показать статус сервиса"
    echo "  logs      - Показать последние записи лога"
    echo "  errors    - Показать последние ошибки"
    echo "  help      - Показать эту справку"
    echo ""
    echo "Примеры:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 logs 50"
    echo "  $0 errors 10"
}

# Основная логика
case "${1:-help}" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    errors)
        show_errors "$2"
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_status "error" "Неизвестная команда: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
