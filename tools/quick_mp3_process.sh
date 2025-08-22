#!/bin/bash

# Быстрая обработка MP3 файлов
# Использование: ./quick_mp3_process.sh [папка] [формат]

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветного текста
print_color() {
    local color=$1
    local text=$2
    echo -e "${color}${text}${NC}"
}

# Проверяем аргументы
if [ $# -eq 0 ]; then
    print_color $RED "❌ Ошибка: Не указана папка для обработки"
    echo "Использование: $0 [папка] [формат]"
    echo ""
    echo "Примеры:"
    echo "  $0 /path/to/folder          # Обработать в формате TXT"
    echo "  $0 /path/to/folder md       # Обработать в формате Markdown"
    echo "  $0 /path/to/folder csv      # Обработать в формате CSV"
    echo "  $0 /path/to/folder json     # Обработать в формате JSON"
    echo "  $0 /path/to/folder srt      # Обработать в формате SRT"
    echo ""
    echo "Доступные форматы: txt, md, csv, json, srt"
    exit 1
fi

# Получаем аргументы
FOLDER="$1"
OUTPUT_FORMAT="${2:-txt}"  # По умолчанию TXT

# Проверяем существование папки
if [ ! -d "$FOLDER" ]; then
    print_color $RED "❌ Ошибка: Папка '$FOLDER' не найдена"
    exit 1
fi

# Проверяем формат
case $OUTPUT_FORMAT in
    txt|md|csv|json|srt)
        ;;
    *)
        print_color $RED "❌ Ошибка: Неподдерживаемый формат '$OUTPUT_FORMAT'"
        echo "Доступные форматы: txt, md, csv, json, srt"
        exit 1
        ;;
esac

# Переходим в корневую директорию проекта
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

print_color $BLUE "🚀 Запуск обработки MP3 файлов..."
print_color $BLUE "📁 Папка: $FOLDER"
print_color $BLUE "📝 Формат: $OUTPUT_FORMAT"
print_color $BLUE "🏠 Корневая директория: $PROJECT_ROOT"
echo ""

# Активируем виртуальное окружение если оно есть
if [ -d "venv" ]; then
    print_color $YELLOW "🐍 Активирую виртуальное окружение..."
    source venv/bin/activate
fi

# Проверяем наличие Python скрипта
if [ ! -f "tools/process_mp3_folders.py" ]; then
    print_color $RED "❌ Ошибка: Скрипт process_mp3_folders.py не найден"
    exit 1
fi

# Запускаем обработку
print_color $GREEN "🎤 Запускаю обработку..."
python tools/process_mp3_folders.py "$FOLDER" --output "$OUTPUT_FORMAT" --recursive

# Проверяем результат
if [ $? -eq 0 ]; then
    print_color $GREEN "✅ Обработка завершена успешно!"
    echo ""
    print_color $BLUE "📋 Результаты сохранены в папке: $FOLDER"
    echo "   Файлы транскриптов имеют имена вида:"
    echo "   - filename_transcript.$OUTPUT_FORMAT"
    echo ""
    print_color $BLUE "📊 Подробная статистика выше"
else
    print_color $RED "❌ Ошибка при обработке"
    exit 1
fi
