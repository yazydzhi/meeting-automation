#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы отслеживания статуса обработки.
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

from processing_status import ProcessingStatus

def test_processing_status():
    """Тестируем систему отслеживания статуса."""
    
    # Тестовая папка
    test_folder = "/Users/azg/Downloads/01 - yazydzhi@gmail.com/2025-08-21 18-00 Тестовая встреча"
    
    print(f"🧪 Тестируем систему отслеживания статуса для папки: {test_folder}")
    
    # Инициализируем отслеживание
    status = ProcessingStatus(test_folder)
    
    # Выводим текущий статус
    print("\n📊 Текущий статус:")
    status.print_summary()
    
    # Проверяем конкретные файлы
    mkv_file = "2025-08-13 13-10-14 (1).mkv"
    mp4_file = "2025-08-13 13-10-14 (1)_compressed.mp4"
    mp3_file = "2025-08-13 13-10-14 (1)_compressed.mp3"
    
    print(f"\n🔍 Проверяем файл: {mkv_file}")
    mkv_status = status.get_file_status(mkv_file)
    if mkv_status:
        print(f"   Статус: {mkv_status['status']}")
        print(f"   Тип: {mkv_status['type']}")
        print(f"   Размер: {mkv_status['size']} байт")
        if mkv_status.get('processing_steps'):
            print("   Этапы обработки:")
            for step in mkv_status['processing_steps']:
                print(f"     - {step['step']}: {step.get('timestamp', 'N/A')}")
    else:
        print("   Файл не найден в отслеживании")
    
    print(f"\n🔍 Проверяем файл: {mp4_file}")
    mp4_status = status.get_file_status(mp4_file)
    if mp4_status:
        print(f"   Статус: {mp4_status['status']}")
        print(f"   Тип: {mp4_status['type']}")
        print(f"   Размер: {mp4_status['size']} байт")
        if mp4_status.get('processing_steps'):
            print("   Этапы обработки:")
            for step in mp4_status['processing_steps']:
                print(f"     - {step['step']}: {step.get('timestamp', 'N/A')}")
    else:
        print("   Файл не найден в отслеживании")
    
    print(f"\n🔍 Проверяем файл: {mp3_file}")
    mp3_status = status.get_file_status(mp3_file)
    if mp3_status:
        print(f"   Статус: {mp3_status['status']}")
        print(f"   Тип: {mp3_status['type']}")
        print(f"   Размер: {mp3_status['size']} байт")
        if mp3_status.get('processing_steps'):
            print("   Этапы обработки:")
            for step in mp3_status['processing_steps']:
                print(f"     - {step['step']}: {step.get('timestamp', 'N/A')}")
    else:
        print("   Файл не найден в отслеживании")
    
    # Проверяем, обработан ли MKV файл
    print(f"\n✅ MKV файл обработан (видео): {status.is_file_processed(mkv_file, 'video_compression')}")
    print(f"✅ MKV файл обработан (аудио): {status.is_file_processed(mkv_file, 'audio_extraction')}")
    
    # Проверяем, обработан ли MP4 файл
    print(f"✅ MP4 файл обработан (видео): {status.is_file_processed(mp4_file, 'video_compression')}")
    print(f"✅ MP4 файл обработан (аудио): {status.is_file_processed(mp4_file, 'audio_extraction')}")
    
    # Проверяем, обработан ли MP3 файл
    print(f"✅ MP3 файл обработан (аудио): {status.is_file_processed(mp3_file, 'audio_extraction')}")
    
    # Показываем содержимое файла статуса
    status_file = Path(test_folder) / '📊 processing_status.json'
    if status_file.exists():
        print(f"\n📄 Содержимое файла статуса:")
        import json
        with open(status_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"\n❌ Файл статуса не найден: {status_file}")

if __name__ == "__main__":
    test_processing_status()
