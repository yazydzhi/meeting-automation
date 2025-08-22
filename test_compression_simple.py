#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Простой тест компрессии видео
"""

import os
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

try:
    from media_processor import MediaProcessor
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_compression_simple():
    """Простой тест компрессии видео."""
    
    # Путь к тестовому видео файлу
    video_path = "data/synced/2025-08-21 18-00 Тестовая встреча/FT - LifePay 20.03.2023.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Видео файл не найден: {video_path}")
        return
    
    print(f"🎬 Тестируем компрессию: {os.path.basename(video_path)}")
    
    # Создаем MediaProcessor (без drive_service для простого теста)
    processor = MediaProcessor(
        drive_service=None,  # Не нужен для простого теста
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
    
    # Тестируем разные настройки компрессии
    test_configs = [
        ("H.264 Medium", "medium", "h264"),
        ("H.264 High", "high", "h264"),
        ("H.265 Medium", "medium", "h265"),
    ]
    
    for config_name, quality, codec in test_configs:
        print(f"\n🎬 Тестируем: {config_name}")
        print(f"   Качество: {quality}, Кодек: {codec}")
        
        # Генерируем имя выходного файла
        output_dir = os.path.dirname(video_path)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(output_dir, f"{base_name}_compressed_{codec}_{quality}.mp4")
        
        print(f"   Входной файл: {os.path.basename(video_path)}")
        print(f"   Выходной файл: {os.path.basename(output_path)}")
        
        # Получаем размер входного файла
        input_size = os.path.getsize(video_path)
        print(f"   Размер входного файла: {processor._format_size(input_size)}")
        
        # Тестируем компрессию
        if processor.compress_video(video_path, output_path, quality, codec):
            # Получаем размер выходного файла
            if os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                compression_ratio = (1 - output_size / input_size) * 100
                
                print(f"   ✅ Компрессия успешна!")
                print(f"   📊 Размер: {processor._format_size(input_size)} → {processor._format_size(output_size)}")
                print(f"   📉 Сжатие: {compression_ratio:.1f}%")
                print(f"   💾 Экономия: {processor._format_size(input_size - output_size)}")
            else:
                print(f"   ❌ Выходной файл не создан")
        else:
            print(f"   ❌ Компрессия не удалась")
        
        print("-" * 50)

if __name__ == "__main__":
    test_compression_simple()
