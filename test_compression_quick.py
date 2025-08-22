#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест компрессии видео (на фрагменте)
"""

import os
import sys
import subprocess
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

try:
    from media_processor import MediaProcessor
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def create_test_video():
    """Создаем небольшой тестовый видео файл."""
    
    output_path = "test_video_short.mp4"
    
    if os.path.exists(output_path):
        print(f"✅ Тестовый файл уже существует: {output_path}")
        return output_path
    
    print("🎬 Создаем тестовый видео файл...")
    
    # Создаем 10-секундный тестовый видео файл
    cmd = [
        'ffmpeg', '-f', 'lavfi', '-i', 'testsrc=duration=10:size=640x480:rate=30',
        '-f', 'lavfi', '-i', 'sine=frequency=1000:duration=10',
        '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
        '-c:a', 'aac', '-b:a', '128k',
        '-y', output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Тестовый файл создан: {output_path}")
            return output_path
        else:
            print(f"❌ Ошибка создания тестового файла: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print("❌ Таймаут создания тестового файла")
        return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def test_compression_quick():
    """Быстрый тест компрессии на небольшом файле."""
    
    # Создаем тестовый видео файл
    test_video = create_test_video()
    if not test_video:
        print("❌ Не удалось создать тестовый файл")
        return
    
    # Проверяем размер
    if os.path.exists(test_video):
        size = os.path.getsize(test_video)
        print(f"📊 Размер тестового файла: {size / 1024 / 1024:.1f} MB")
    
    print(f"\n🎬 Тестируем компрессию: {os.path.basename(test_video)}")
    
    # Создаем MediaProcessor
    processor = MediaProcessor(
        drive_service=None,
        output_format='mp3',
        video_compression=True,
        video_quality='medium',
        video_codec='h264'
    )
    
    # Проверяем доступность ffmpeg
    if not processor.ffmpeg_available:
        print("❌ ffmpeg недоступен")
        return
    
    print("✅ ffmpeg доступен")
    
    # Тестируем быструю компрессию
    test_configs = [
        ("H.264 Fast", "low", "h264"),
        ("H.264 Medium", "medium", "h264"),
    ]
    
    for config_name, quality, codec in test_configs:
        print(f"\n🎬 Тестируем: {config_name}")
        print(f"   Качество: {quality}, Кодек: {codec}")
        
        # Генерируем имя выходного файла
        output_path = f"test_video_compressed_{codec}_{quality}.mp4"
        
        print(f"   Входной файл: {os.path.basename(test_video)}")
        print(f"   Выходной файл: {output_path}")
        
        # Получаем размер входного файла
        input_size = os.path.getsize(test_video)
        print(f"   Размер входного файла: {processor._format_size(input_size)}")
        
        # Тестируем компрессию
        start_time = os.times().elapsed
        if processor.compress_video(test_video, output_path, quality, codec):
            end_time = os.times().elapsed
            processing_time = end_time - start_time
            
            # Получаем размер выходного файла
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                compression_ratio = (1 - output_size / input_size) * 100
                
                print(f"   ✅ Компрессия успешна!")
                print(f"   📊 Размер: {processor._format_size(input_size)} → {processor._format_size(output_size)}")
                print(f"   📉 Сжатие: {compression_ratio:.1f}%")
                print(f"   💾 Экономия: {processor._format_size(input_size - output_size)}")
                print(f"   ⏱️ Время обработки: {processing_time:.1f} сек")
            else:
                print(f"   ❌ Выходной файл не создан")
        else:
            print(f"   ❌ Компрессия не удалась")
        
        print("-" * 50)
    
    # Очистка тестовых файлов
    print("\n🧹 Очистка тестовых файлов...")
    for file in [test_video, "test_video_compressed_h264_low.mp4", "test_video_compressed_h264_medium.mp4"]:
        if os.path.exists(file):
            os.remove(file)
            print(f"   Удален: {file}")

if __name__ == "__main__":
    test_compression_quick()
