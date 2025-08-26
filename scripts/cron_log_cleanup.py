#!/usr/bin/env python3
"""
Скрипт для автоматической очистки логов через cron.
Запускается ежедневно для поддержания чистоты системы логов.
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scripts.log_manager import LogManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)


def main():
    """Основная функция для cron."""
    try:
        # Создаем менеджер логов
        log_manager = LogManager()
        
        # Выполняем автоматическую очистку
        log_manager.cleanup_old_logs()
        
        # Выполняем ротацию больших файлов
        log_manager.rotate_logs()
        
        print("✅ Автоматическая очистка логов завершена")
        
    except Exception as e:
        print(f"❌ Ошибка автоматической очистки логов: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
