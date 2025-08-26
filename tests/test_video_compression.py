#!/usr/bin/env python3
"""
Тестирование сжатия видео и извлечения аудио.
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Добавляем путь к корневой директории проекта для импорта модулей
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from src.config_manager import ConfigManager
    from src.media_processor import get_media_processor
    from src.drive_sync import get_drive_sync
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)

def test_video_compression():
    """Тестирование сжатия видео и извлечения аудио."""
    
    try:
        print("\n🔍 Получаем Google сервисы...")
        
        # Загружаем переменные окружения
        load_dotenv()
        
        # Получаем параметры
        parent_id = os.getenv('PERSONAL_DRIVE_PARENT_ID')
        sync_root = os.getenv('MEDIA_SYNC_ROOT', 'data/synced')
        
        if not parent_id:
            print("❌ Не указан PERSONAL_DRIVE_PARENT_ID")
            return
        
        print(f"✅ Google Drive сервис доступен")
        print(f"📁 PERSONAL_DRIVE_PARENT_ID: {parent_id}")
        print(f"📁 MEDIA_SYNC_ROOT: {sync_root}")
        
        print("\n🔧 Создаем модули с компрессией видео...")
        
        # Тестируем разные настройки компрессии
        compression_configs = [
            ("H.264 Medium", True, "medium", "h264"),
            ("H.264 High", True, "high", "h264"),
            ("H.265 Medium", True, "medium", "h265"),
            ("VP9 Medium", True, "medium", "vp9"),
        ]
        
        for config_name, compression, quality, codec in compression_configs:
            print(f"\n🎬 Тестируем конфигурацию: {config_name}")
            print(f"   Компрессия: {compression}, Качество: {quality}, Кодек: {codec}")
            
            # Создаем конфигурацию с помощью переменных окружения
            os.environ['VIDEO_COMPRESSION'] = str(compression).lower()
            os.environ['VIDEO_QUALITY'] = quality
            os.environ['VIDEO_CODEC'] = codec
            os.environ['MEDIA_OUTPUT_FORMAT'] = 'mp3'
            
            # Создаем ConfigManager с обновленными настройками
            config_manager = ConfigManager()
            
            # Создаем логгер для теста
            logger = logging.getLogger("test_video_compression")
            
            # Создаем медиа-процессор
            media_processor = get_media_processor(
                config_manager=config_manager,
                logger=logger
            )
            
            if not media_processor:
                print("❌ Не удалось создать модуль")
                continue
            
            print("✅ Модуль создан")
            
            # Обрабатываем медиа файлы
            print(f"\n🎬 Обрабатываем медиа файлы...")
            media_results = media_processor.process_media(quality)
            
            print(f"📊 Результаты обработки:")
            if isinstance(media_results, dict):
                for key, value in media_results.items():
                    if key == 'results':
                        for result in value:
                            print(f"  - Аккаунт: {result.get('account_type', 'unknown')}")
                            print(f"    - Обработано: {result.get('processed', 0)}")
                            print(f"    - Синхронизировано: {result.get('synced', 0)}")
                    else:
                        print(f"  - {key}: {value}")
            else:
                print(f"  - {media_results}")
            
            # Если есть ошибки, показываем их
            if isinstance(media_results, dict) and 'errors' in media_results and media_results['errors']:
                print(f"❌ Ошибки:")
                for error in media_results['errors']:
                    print(f"  - {error}")
    
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_video_compression()
