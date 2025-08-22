#!/usr/bin/env python3
"""
Автоматическая обработка MP3 файлов из папок
Обрабатывает все MP3 файлы в указанных папках и сохраняет транскрипты в тех же папках
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
import time

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from src.audio_processor import AudioProcessor
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что вы находитесь в корневой директории проекта")
    sys.exit(1)

def setup_logging():
    """Настройка логирования"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/mp3_processing.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

def find_mp3_files(root_path: str, recursive: bool = True) -> List[Path]:
    """
    Найти все MP3 файлы в указанной папке
    
    Args:
        root_path: Путь к корневой папке
        recursive: Искать рекурсивно в подпапках
        
    Returns:
        Список путей к MP3 файлам
    """
    mp3_files = []
    root = Path(root_path)
    
    if not root.exists():
        print(f"❌ Папка не найдена: {root_path}")
        return []
    
    if recursive:
        # Рекурсивный поиск
        for mp3_file in root.rglob("*.mp3"):
            mp3_files.append(mp3_file)
    else:
        # Только в текущей папке
        for mp3_file in root.glob("*.mp3"):
            mp3_files.append(mp3_file)
    
    return sorted(mp3_files)

def process_mp3_file(audio_processor: AudioProcessor, mp3_file: Path, output_format: str, force: bool = False) -> Dict[str, Any]:
    """
    Обработать один MP3 файл
    
    Args:
        audio_processor: Экземпляр аудио процессора
        mp3_file: Путь к MP3 файлу
        output_format: Формат вывода
        force: Принудительная обработка даже если файл уже существует
        
    Returns:
        Результат обработки
    """
    # Формируем имя выходного файла в начале функции
    if output_format == 'txt':
        output_file = mp3_file.parent / f"{mp3_file.stem}_transcript.txt"
    elif output_format == 'md':
        output_file = mp3_file.parent / f"{mp3_file.stem}_transcript.md"
    elif output_format == 'csv':
        output_file = mp3_file.parent / f"{mp3_file.stem}_transcript.csv"
    else:
        output_file = mp3_file.parent / f"{mp3_file.stem}_transcript.{output_format}"
    
    try:
        print(f"🎤 Обрабатываю: {mp3_file.name}")
        
        # Проверяем, не обработан ли уже файл
        if output_file.exists() and not force:
            print(f"   ✅ Транскрипт уже существует: {output_file.name}")
            return {
                'status': 'skipped',
                'file': str(mp3_file),
                'output': str(output_file),
                'reason': 'already_exists'
            }
        
        # Обрабатываем файл
        start_time = time.time()
        result = audio_processor.process_audio_file(str(mp3_file), output_format)
        processing_time = time.time() - start_time
        
        if result and result.get('transcription'):
            print(f"   ✅ Транскрипция завершена за {processing_time:.1f}с")
            print(f"   📝 Результат: {output_file.name}")
            print(f"   👥 Участников: {result.get('speakers_count', 0)}")
            
            return {
                'status': 'success',
                'file': str(mp3_file),
                'output': str(output_file),
                'processing_time': processing_time,
                'speakers_count': result.get('speakers_count', 0),
                'segments_count': result.get('segments_count', 0)
            }
        else:
            print(f"   ❌ Транскрипция не удалась")
            return {
                'status': 'error',
                'file': str(mp3_file),
                'output': str(output_file),
                'error': 'transcription_failed'
            }
            
    except Exception as e:
        print(f"   ❌ Ошибка обработки: {e}")
        return {
            'status': 'error',
            'file': str(mp3_file),
            'output': str(output_file),
            'error': str(e)
        }

def create_md_transcript(result: Dict[str, Any], mp3_file: Path) -> str:
    """Создать Markdown транскрипт"""
    md_content = f"# Транскрипция: {mp3_file.name}\n\n"
    md_content += f"**Файл:** {mp3_file.name}\n"
    md_content += f"**Размер:** {result.get('file_size', 0)} байт\n"
    md_content += f"**Длительность:** {result.get('duration', 0)}ms\n"
    md_content += f"**Сегментов:** {result.get('segments_count', 0)}\n"
    md_content += f"**Участников:** {result.get('speakers_count', 0)}\n"
    md_content += f"**Модель Whisper:** {result.get('whisper_model', 'unknown')}\n"
    md_content += f"**Язык:** {result.get('language', 'unknown')}\n\n"
    
    md_content += "---\n\n"
    
    if result.get('transcription'):
        for speaker in result['transcription']:
            md_content += f"## {speaker['speaker_id']}\n\n"
            md_content += f"**Общая длительность:** {speaker['total_duration']}ms\n\n"
            
            for segment in speaker['segments']:
                start_time = segment['start_time'] / 1000  # в секунды
                end_time = segment['end_time'] / 1000
                md_content += f"**[{start_time:.1f}s - {end_time:.1f}s]** {segment['text']}\n\n"
    
    return md_content

def create_csv_transcript(result: Dict[str, Any], mp3_file: Path) -> str:
    """Создать CSV транскрипт"""
    csv_content = "speaker_id,start_time,end_time,duration,text\n"
    
    if result.get('transcription'):
        for speaker in result['transcription']:
            for segment in speaker['segments']:
                start_time = segment['start_time'] / 1000  # в секунды
                end_time = segment['end_time'] / 1000
                duration = segment['duration'] / 1000
                
                # Экранируем запятые и кавычки в тексте
                text = segment['text'].replace('"', '""')
                csv_content += f'"{speaker["speaker_id"]}",{start_time:.1f},{end_time:.1f},{duration:.1f},"{text}"\n'
    
    return csv_content

def save_transcript(result: Dict[str, Any], mp3_file: Path, output_format: str, output_file: Path):
    """Сохранить транскрипт в нужном формате"""
    try:
        if output_format == 'md':
            content = create_md_transcript(result, mp3_file)
        elif output_format == 'csv':
            content = create_csv_transcript(result, mp3_file)
        else:
            # Для других форматов используем встроенную функцию
            return
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"   💾 Сохранен в формате {output_format.upper()}")
        
    except Exception as e:
        print(f"   ❌ Ошибка сохранения {output_format}: {e}")

def process_folders(folders: List[str], output_format: str = 'txt', recursive: bool = True, force: bool = False, config_file: str = None):
    """
    Обработать MP3 файлы в указанных папках
    
    Args:
        folders: Список путей к папкам
        output_format: Формат вывода (txt, md, csv, json, srt)
        recursive: Искать рекурсивно в подпапках
        force: Принудительная обработка
        config_file: Путь к конфигурационному файлу
    """
    logger = setup_logging()
    
    print(f"🚀 Начинаю обработку MP3 файлов...")
    print(f"📁 Папки: {', '.join(folders)}")
    print(f"📝 Формат вывода: {output_format.upper()}")
    print(f"🔄 Рекурсивный поиск: {'Да' if recursive else 'Нет'}")
    print(f"⚡ Принудительная обработка: {'Да' if force else 'Нет'}")
    print("-" * 60)
    
    # Инициализируем аудио процессор
    try:
        audio_processor = AudioProcessor(config_file)
        print("✅ Аудио процессор инициализирован")
    except Exception as e:
        print(f"❌ Ошибка инициализации аудио процессора: {e}")
        return
    
    # Статистика
    total_files = 0
    processed_files = 0
    skipped_files = 0
    error_files = 0
    total_processing_time = 0
    
    # Обрабатываем каждую папку
    for folder in folders:
        print(f"\n📂 Обрабатываю папку: {folder}")
        
        # Ищем MP3 файлы
        mp3_files = find_mp3_files(folder, recursive)
        
        if not mp3_files:
            print(f"   ℹ️  MP3 файлы не найдены")
            continue
        
        print(f"   🎵 Найдено MP3 файлов: {len(mp3_files)}")
        
        # Обрабатываем файлы
        for mp3_file in mp3_files:
            total_files += 1
            
            # Обрабатываем файл
            result = process_mp3_file(audio_processor, mp3_file, output_format, force)
            
            # Обновляем статистику
            if result['status'] == 'success':
                processed_files += 1
                total_processing_time += result.get('processing_time', 0)
                
                # Для md и csv форматов сохраняем дополнительно
                if output_format in ['md', 'csv']:
                    output_file = Path(result['output'])
                    save_transcript(result, mp3_file, output_format, output_file)
                    
            elif result['status'] == 'skipped':
                skipped_files += 1
            else:
                error_files += 1
    
    # Выводим итоговую статистику
    print("\n" + "=" * 60)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print("=" * 60)
    print(f"📁 Всего папок: {len(folders)}")
    print(f"🎵 Всего MP3 файлов: {total_files}")
    print(f"✅ Успешно обработано: {processed_files}")
    print(f"⏭️  Пропущено: {skipped_files}")
    print(f"❌ Ошибок: {error_files}")
    
    if processed_files > 0:
        avg_time = total_processing_time / processed_files
        print(f"⏱️  Среднее время обработки: {avg_time:.1f}с")
        print(f"⏱️  Общее время обработки: {total_processing_time:.1f}с")
    
    # Очищаем временные файлы
    try:
        audio_processor.cleanup_temp_files()
        print("🧹 Временные файлы очищены")
    except Exception as e:
        print(f"⚠️  Не удалось очистить временные файлы: {e}")
    
    print("🏁 Обработка завершена!")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Автоматическая обработка MP3 файлов из папок')
    parser.add_argument('folders', nargs='+', help='Пути к папкам для обработки')
    parser.add_argument('--output', choices=['txt', 'md', 'csv', 'json', 'srt'], default='txt',
                       help='Формат вывода (по умолчанию: txt)')
    parser.add_argument('--recursive', action='store_true', default=True,
                       help='Искать MP3 файлы рекурсивно в подпапках (по умолчанию: Да)')
    parser.add_argument('--no-recursive', dest='recursive', action='store_false',
                       help='Искать MP3 файлы только в указанных папках')
    parser.add_argument('--force', action='store_true',
                       help='Принудительная обработка всех файлов (перезаписать существующие)')
    parser.add_argument('--config', help='Путь к конфигурационному файлу')
    
    args = parser.parse_args()
    
    # Проверяем существование папок
    for folder in args.folders:
        if not os.path.exists(folder):
            print(f"❌ Папка не найдена: {folder}")
            sys.exit(1)
    
    # Обрабатываем папки
    process_folders(
        folders=args.folders,
        output_format=args.output,
        recursive=args.recursive,
        force=args.force,
        config_file=args.config
    )

if __name__ == '__main__':
    main()
