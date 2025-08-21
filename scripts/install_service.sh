#!/bin/bash

# Скрипт установки сервиса автоматизации встреч
# Поддерживает macOS (launchd) и Linux (systemd)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="meeting-automation"

echo "🚀 Установка сервиса автоматизации встреч..."
echo "📁 Директория проекта: $PROJECT_DIR"

# Проверяем, что мы в правильной директории
if [[ ! -f "$PROJECT_DIR/meeting_automation_personal_only.py" ]]; then
    echo "❌ Ошибка: Не найден основной файл проекта"
    exit 1
fi

# Проверяем виртуальное окружение
if [[ ! -d "$PROJECT_DIR/venv" ]]; then
    echo "❌ Ошибка: Виртуальное окружение не найдено"
    echo "Сначала создайте виртуальное окружение: python -m venv venv"
    exit 1
fi

# Определяем ОС
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "❌ Неподдерживаемая ОС: $OSTYPE"
    exit 1
fi

echo "🖥️  Операционная система: $OS"

# Создаем директории
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/data/synced"

# Устанавливаем права
chmod +x "$PROJECT_DIR/src/service_manager.py"

if [[ "$OS" == "macos" ]]; then
    echo "🍎 Устанавливаю launchd сервис для macOS..."
    
    # Копируем plist файл
    PLIST_DIR="$HOME/Library/LaunchAgents"
    mkdir -p "$PLIST_DIR"
    
    # Заменяем пути в plist файле
    sed "s|/Users/azg/repository/meeting_automation|$PROJECT_DIR|g" \
        "$PROJECT_DIR/launchd/com.yazydzhi.meeting-automation.plist" \
        > "$PLIST_DIR/com.yazydzhi.meeting-automation.plist"
    
    # Загружаем сервис
    launchctl unload "$PLIST_DIR/com.yazydzhi.meeting-automation.plist" 2>/dev/null || true
    launchctl load "$PLIST_DIR/com.yazydzhi.meeting-automation.plist"
    
    echo "✅ Сервис установлен и запущен"
    echo "📋 Команды управления:"
    echo "  Запуск:   launchctl start com.yazydzhi.meeting-automation"
    echo "  Остановка: launchctl stop com.yazydzhi.meeting-automation"
    echo "  Статус:   launchctl list | grep meeting-automation"
    echo "  Логи:     tail -f $PROJECT_DIR/logs/service.log"
    
elif [[ "$OS" == "linux" ]]; then
    echo "🐧 Устанавливаю systemd сервис для Linux..."
    
    # Проверяем права sudo
    if [[ $EUID -ne 0 ]]; then
        echo "❌ Для установки systemd сервиса требуются права администратора"
        echo "Запустите скрипт с sudo: sudo $0"
        exit 1
    fi
    
    # Копируем service файл
    SERVICE_DIR="/etc/systemd/system"
    sed "s|/Users/azg/repository/meeting_automation|$PROJECT_DIR|g" \
        "$PROJECT_DIR/systemd/meeting-automation.service" \
        > "$SERVICE_DIR/meeting-automation.service"
    
    # Заменяем пользователя и группу
    CURRENT_USER=$(whoami)
    CURRENT_GROUP=$(id -gn)
    sed -i "s/User=azg/User=$CURRENT_USER/g" "$SERVICE_DIR/meeting-automation.service"
    sed -i "s/Group=azg/Group=$CURRENT_GROUP/g" "$SERVICE_DIR/meeting-automation.service"
    
    # Перезагружаем systemd и включаем сервис
    systemctl daemon-reload
    systemctl enable meeting-automation.service
    systemctl start meeting-automation.service
    
    echo "✅ Сервис установлен и запущен"
    echo "📋 Команды управления:"
    echo "  Запуск:   sudo systemctl start meeting-automation"
    echo "  Остановка: sudo systemctl stop meeting-automation"
    echo "  Статус:   sudo systemctl status meeting-automation"
    echo "  Логи:     sudo journalctl -u meeting-automation -f"
fi

echo ""
echo "🎉 Установка завершена!"
echo "📱 Сервис будет автоматически запускаться при загрузке системы"
echo "📊 Логи доступны в директории: $PROJECT_DIR/logs/"
echo ""
echo "🔧 Для тестирования запустите:"
echo "   cd $PROJECT_DIR && source venv/bin/activate"
echo "   python src/service_manager.py --interval 60"
