#!/usr/bin/env python3
"""
Скрипт для очистки резервных копий файлов статуса.
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта")
    sys.exit(1)


def cleanup_backup_files(root_path: str) -> int:
    """Очистить резервные копии файлов."""
    backup_count = 0
    
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file.endswith(".backup"):
                backup_path = os.path.join(root, file)
                try:
                    os.remove(backup_path)
                    print(f"🗑️ Удалена резервная копия: {backup_path}")
                    backup_count += 1
                except Exception as e:
                    print(f"❌ Ошибка удаления {backup_path}: {e}")
    
    return backup_count


def main():
    """Основная функция."""
    print("🗑️ Скрипт очистки резервных копий")
    print("=" * 40)
    
    # Загружаем конфигурацию
    try:
        config_manager = ConfigManager()
        print("✅ Конфигурация загружена")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not config_manager.validate_config():
        print("❌ Конфигурация некорректна")
        sys.exit(1)
    
    total_backup_count = 0
    
    # Очищаем резервные копии в личном аккаунте
    if config_manager.is_personal_enabled():
        personal_config = config_manager.get_personal_config()
        personal_folder = personal_config.get('local_drive_root')
        
        if personal_folder and os.path.exists(personal_folder):
            print(f"\n👤 Очистка личного аккаунта: {personal_folder}")
            backup_count = cleanup_backup_files(personal_folder)
            total_backup_count += backup_count
            print(f"✅ Удалено {backup_count} резервных копий")
    
    # Очищаем резервные копии в рабочем аккаунте
    if config_manager.is_work_enabled():
        work_config = config_manager.get_work_config()
        work_folder = work_config.get('local_drive_root')
        
        if work_folder and os.path.exists(work_folder):
            print(f"\n🏢 Очистка рабочего аккаунта: {work_folder}")
            backup_count = cleanup_backup_files(work_folder)
            total_backup_count += backup_count
            print(f"✅ Удалено {backup_count} резервных копий")
    
    print(f"\n🎉 Очистка завершена! Всего удалено: {total_backup_count} резервных копий")


if __name__ == "__main__":
    main()
