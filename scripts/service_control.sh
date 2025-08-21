#!/bin/bash

# Скрипт управления сервисом автоматизации встреч
# Поддерживает macOS (launchd) и Linux (systemd)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="meeting-automation"

# Определяем ОС
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "❌ Неподдерживаемая ОС: $OSTYPE"
    exit 1
fi

# Функция для macOS
macos_control() {
    local action="$1"
    local plist="$HOME/Library/LaunchAgents/com.yazydzhi.meeting-automation.plist"
    
    case "$action" in
        start)
            echo "🚀 Запуск сервиса..."
            launchctl load "$plist" 2>/dev/null || true
            launchctl start com.yazydzhi.meeting-automation
            echo "✅ Сервис запущен"
            ;;
        stop)
            echo "🛑 Остановка сервиса..."
            launchctl stop com.yazydzhi.meeting-automation
            launchctl unload "$plist" 2>/dev/null || true
            echo "✅ Сервис остановлен"
            ;;
        restart)
            echo "🔄 Перезапуск сервиса..."
            launchctl stop com.yazydzhi.meeting-automation 2>/dev/null || true
            launchctl unload "$plist" 2>/dev/null || true
            sleep 2
            launchctl load "$plist"
            launchctl start com.yazydzhi.meeting-automation
            echo "✅ Сервис перезапущен"
            ;;
        status)
            echo "📊 Статус сервиса:"
            if launchctl list | grep -q "com.yazydzhi.meeting-automation"; then
                echo "✅ Сервис запущен"
                launchctl list | grep "com.yazydzhi.meeting-automation"
            else
                echo "❌ Сервис не запущен"
            fi
            ;;
        logs)
            echo "📋 Последние логи сервиса:"
            if [[ -f "$PROJECT_DIR/logs/service.log" ]]; then
                tail -n 50 "$PROJECT_DIR/logs/service.log"
            else
                echo "❌ Файл логов не найден"
            fi
            ;;
        follow-logs)
            echo "📋 Отслеживание логов в реальном времени (Ctrl+C для выхода):"
            if [[ -f "$PROJECT_DIR/logs/service.log" ]]; then
                tail -f "$PROJECT_DIR/logs/service.log"
            else
                echo "❌ Файл логов не найден"
            fi
            ;;
        *)
            echo "❌ Неизвестное действие: $action"
            show_help
            exit 1
            ;;
    esac
}

# Функция для Linux
linux_control() {
    local action="$1"
    
    case "$action" in
        start)
            echo "🚀 Запуск сервиса..."
            sudo systemctl start meeting-automation
            echo "✅ Сервис запущен"
            ;;
        stop)
            echo "🛑 Остановка сервиса..."
            sudo systemctl stop meeting-automation
            echo "✅ Сервис остановлен"
            ;;
        restart)
            echo "🔄 Перезапуск сервиса..."
            sudo systemctl restart meeting-automation
            echo "✅ Сервис перезапущен"
            ;;
        status)
            echo "📊 Статус сервиса:"
            sudo systemctl status meeting-automation --no-pager
            ;;
        logs)
            echo "📋 Последние логи сервиса:"
            sudo journalctl -u meeting-automation --no-pager -n 50
            ;;
        follow-logs)
            echo "📋 Отслеживание логов в реальном времени (Ctrl+C для выхода):"
            sudo journalctl -u meeting-automation -f
            ;;
        enable)
            echo "🔧 Включение автозапуска сервиса..."
            sudo systemctl enable meeting-automation
            echo "✅ Автозапуск включен"
            ;;
        disable)
            echo "🔧 Отключение автозапуска сервиса..."
            sudo systemctl disable meeting-automation
            echo "✅ Автозапуск отключен"
            ;;
        *)
            echo "❌ Неизвестное действие: $action"
            show_help
            exit 1
            ;;
    esac
}

# Показать справку
show_help() {
    echo "🔧 Управление сервисом автоматизации встреч"
    echo ""
    echo "Использование: $0 <действие>"
    echo ""
    echo "Действия:"
    echo "  start         - Запустить сервис"
    echo "  stop          - Остановить сервис"
    echo "  restart       - Перезапустить сервис"
    echo "  status        - Показать статус"
    echo "  logs          - Показать последние логи"
    echo "  follow-logs   - Отслеживать логи в реальном времени"
    
    if [[ "$OS" == "linux" ]]; then
        echo "  enable        - Включить автозапуск"
        echo "  disable       - Отключить автозапуск"
    fi
    
    echo ""
    echo "Примеры:"
    echo "  $0 start"
    echo "  $0 status"
    echo "  $0 follow-logs"
}

# Основная логика
if [[ $# -eq 0 ]]; then
    show_help
    exit 1
fi

action="$1"

echo "🖥️  Операционная система: $OS"
echo "📁 Директория проекта: $PROJECT_DIR"
echo ""

if [[ "$OS" == "macos" ]]; then
    macos_control "$action"
elif [[ "$OS" == "linux" ]]; then
    linux_control "$action"
fi
