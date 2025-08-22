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

def test_audio_processor(audio_file: str, config_file: str = None, output_format: str = 'json'):
    """Тестирование аудио процессора"""
    try:
        print(f"🎤 Тестирование аудио процессора...")
        print(f"📁 Аудио файл: {audio_file}")
        print(f"⚙️  Конфигурация: {config_file or 'по умолчанию'}")
        print(f"📝 Формат вывода: {output_format}")
        print("-" * 50)
        
        # Проверяем существование файла
        if not os.path.exists(audio_file):
            print(f"❌ Аудио файл не найден: {audio_file}")
            return False
            
        # Создаем процессор
        processor = AudioProcessor(config_file)
        print("✅ Аудио процессор инициализирован")
        
        # Обрабатываем файл
        print("🔄 Начинаю обработку аудио...")
        result = processor.process_audio_file(audio_file, output_format)
        
        if result:
            print("✅ Обработка завершена успешно!")
            print(f"📊 Статистика:")
            print(f"   📁 Файл: {result['file_path']}")
            print(f"   📏 Размер: {result['file_size']} байт")
            print(f"   ⏱️  Длительность: {result['duration']}ms")
            print(f"   🔢 Сегментов: {result['segments_count']}")
            print(f"   👥 Участников: {result['speakers_count']}")
            print(f"   🤖 Модель Whisper: {result['whisper_model']}")
            print(f"   🌍 Язык: {result['language']}")
            
            # Показываем участников
            if result['transcription']:
                print(f"\n👥 Участники разговора:")
                for i, speaker in enumerate(result['transcription'], 1):
                    print(f"   {speaker['speaker_id']}:")
                    print(f"      ⏱️  Общая длительность: {speaker['total_duration']}ms")
                    print(f"      📝 Сегментов: {len(speaker['segments'])}")
                    
                    # Показываем первые несколько сегментов
                    for j, segment in enumerate(speaker['segments'][:3], 1):
                        text = segment['text'][:100] + "..." if len(segment['text']) > 100 else segment['text']
                        print(f"         {j}. [{segment['start_time']}-{segment['end_time']}ms] {text}")
                    
                    if len(speaker['segments']) > 3:
                        print(f"         ... и еще {len(speaker['segments']) - 3} сегментов")
                    print()
            
            return True
        else:
            print("❌ Обработка не удалась")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

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
    success = test_audio_processor(args.audio_file, args.config, args.output)
    
    # Очищаем временные файлы если нужно
    if args.cleanup and success:
        try:
            processor = AudioProcessor(args.config)
            processor.cleanup_temp_files()
            print("🧹 Временные файлы очищены")
        except Exception as e:
            print(f"⚠️ Не удалось очистить временные файлы: {e}")
    
    # Результат
    if success:
        print("🎉 Тестирование завершено успешно!")
        sys.exit(0)
    else:
        print("❌ Тестирование завершено с ошибками")
        sys.exit(1)

if __name__ == '__main__':
    main()
