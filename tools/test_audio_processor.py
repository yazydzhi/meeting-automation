#!/usr/bin/env python3
"""
Тестирование аудио процессора с Whisper
"""

import os
import sys
import argparse
from pathlib import Path

# Добавляем src в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.audio_processor import AudioProcessor
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что вы находитесь в корневой директории проекта")
    sys.exit(1)

def test_audio_processor(audio_file_path: str, config_file: str = None, output_format: str = 'json'):
    """Тестирование аудио процессора"""
    print("🎤 Тестирование аудио процессора...")
    print(f"📁 Аудио файл: {audio_file_path}")
    print(f"⚙️  Конфигурация: {'по умолчанию' if not config_file else config_file}")
    print(f"📝 Формат вывода: {output_format}")
    print("-" * 50)
    
    try:
        # Инициализируем процессор
        processor = AudioProcessor(config_file)
        print("✅ Аудио процессор инициализирован")
        
        # Обрабатываем аудио
        print("🔄 Начинаю обработку аудио...")
        result = processor.process_audio_file(audio_file_path, output_format)
        
        print("✅ Обработка завершена успешно!")
        print("📊 Статистика:")
        print(f"   📁 Файл: {result.get('file_path', 'N/A')}")
        print(f"   📏 Размер: {result.get('file_size', 'N/A')} байт")
        print(f"   ⏱️  Длительность: {result.get('total_duration', 'N/A')} мс")
        print(f"   🔢 Сегментов: {result.get('total_segments', 'N/A')}")
        print(f"   👥 Спикеров: {len(result.get('speakers', {}))}")
        
        # Показываем детали по спикерам
        if result.get('speakers'):
            print("\n🗣️  Детали по спикерам:")
            for speaker, segments in result['speakers'].items():
                print(f"   {speaker}: {len(segments)} сегментов")
                total_text = sum(len(seg.get('text', '')) for seg in segments)
                print(f"      Общий текст: {total_text} символов")
        
        return result
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return None

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Тестирование аудио процессора')
    parser.add_argument('audio_file', help='Путь к аудио файлу для тестирования')
    parser.add_argument('--config', help='Путь к конфигурационному файлу')
    parser.add_argument('--output', choices=['json', 'txt', 'srt'], default='json',
                       help='Формат вывода (по умолчанию: json)')
    parser.add_argument('--cleanup', action='store_true', help='Очистить временные файлы')
    
    args = parser.parse_args()
    
    # Тестируем процессор
    result = test_audio_processor(args.audio_file, args.config, args.output)
    
    # Очищаем временные файлы если нужно
    if args.cleanup and result:
        try:
            processor = AudioProcessor(args.config)
            processor.cleanup_temp_files()
            print("🧹 Временные файлы очищены")
        except Exception as e:
            print(f"⚠️ Не удалось очистить временные файлы: {e}")
    
    # Результат
    if result:
        print("🎉 Тестирование завершено успешно!")
        sys.exit(0)
    else:
        print("❌ Тестирование завершено с ошибками")
        sys.exit(1)

if __name__ == '__main__':
    main()
