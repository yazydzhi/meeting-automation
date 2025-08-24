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
    test_folder = "/Users/azg/Downloads/01 - yazydzhi@gmail.com/2025-08-21 22-00 Тетсовая встеча"
    
    print(f"🧪 Тестируем систему отслеживания статуса для папки: {test_folder}")
    
    # Инициализируем отслеживание
    status = ProcessingStatus(test_folder)
    
    # Выводим текущий статус
    print("\n📊 Текущий статус:")
    status.print_summary()
    
    # Проверяем конкретные файлы
    mov_file = "Отдел развития ЭлРег в отделениях банков (1).mov"
    mp4_file = "Отдел развития ЭлРег в отделениях банков (1)_compressed.mp4"
    
    print(f"\n🔍 Проверяем файл: {mov_file}")
    mov_status = status.get_file_status(mov_file)
    if mov_status:
        print(f"   Статус: {mov_status['status']}")
        print(f"   Тип: {mov_status['type']}")
        print(f"   Размер: {mov_status['size']} байт")
        if mov_status.get('processing_steps'):
            print("   Этапы обработки:")
            for step in mov_status['processing_steps']:
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
    
    # Проверяем, обработан ли MOV файл
    print(f"\n✅ MOV файл обработан (видео): {status.is_file_processed(mov_file, 'video_compression')}")
    print(f"✅ MOV файл обработан (аудио): {status.is_file_processed(mov_file, 'audio_extraction')}")
    
    # Проверяем, обработан ли MP4 файл
    print(f"✅ MP4 файл обработан (видео): {status.is_file_processed(mp4_file, 'video_compression')}")
    print(f"✅ MP4 файл обработан (аудио): {status.is_file_processed(mp4_file, 'audio_extraction')}")
    
    # Показываем содержимое файла статуса
    status_file = Path(test_folder) / '.processing_status.json'
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
