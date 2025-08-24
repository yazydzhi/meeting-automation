#!/usr/bin/env python3
"""
Полная обработка видео файла по всему флоу:
1. Сжатие видео
2. Извлечение аудио
3. Транскрипция аудио
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio_processor import AudioProcessor
from src.config_manager import ConfigManager

def compress_video(input_path: str, output_path: str, quality: str = 'medium', codec: str = 'h264') -> bool:
    """Сжимает видео файл для уменьшения размера."""
    try:
        print(f"🎥 Сжатие видео {os.path.basename(input_path)}...")
        
        # Настройки качества для разных уровней
        if quality == 'low':
            crf = '28'  # Высокое сжатие
            preset = 'ultrafast'
        elif quality == 'medium':
            crf = '23'  # Среднее сжатие
            preset = 'fast'
        elif quality == 'high':
            crf = '18'  # Низкое сжатие
            preset = 'medium'
        else:  # ultra
            crf = '15'  # Минимальное сжатие
            preset = 'slow'
        
        video_cmd = [
            'ffmpeg', '-i', input_path,
            '-c:v', 'libx264',
            '-crf', crf,
            '-preset', preset,
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',
            '-y',
            output_path
        ]
        
        print(f"🔧 Команда: {' '.join(video_cmd)}")
        
        result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            print(f"✅ Видео сжато: {os.path.basename(output_path)}")
            return True
        else:
            print(f"❌ Ошибка сжатия: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка сжатия видео: {e}")
        return False

def extract_audio(input_path: str, output_path: str, quality: str = 'medium') -> bool:
    """Извлекает аудио из видео файла."""
    try:
        print(f"🎵 Извлечение аудио из {os.path.basename(input_path)}...")
        
        # Настройки качества
        if quality == 'low':
            bitrate = '64k'
            sample_rate = '22050'
        elif quality == 'medium':
            bitrate = '128k'
            sample_rate = '44100'
        else:  # high
            bitrate = '256k'
            sample_rate = '48000'
        
        audio_cmd = [
            'ffmpeg',
            '-i', input_path,
            '-vn',  # Без видео
            '-acodec', 'libmp3lame',
            '-ab', bitrate,
            '-ar', sample_rate,
            '-y',
            output_path
        ]
        
        print(f"🔧 Команда: {' '.join(audio_cmd)}")
        
        result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            print(f"✅ Аудио извлечено: {os.path.basename(output_path)}")
            return True
        else:
            print(f"❌ Ошибка извлечения аудио: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка извлечения аудио: {e}")
        return False

def process_video_full_flow(video_path: str, audio_format: str = 'mp3', 
                           quality: str = 'medium', codec: str = 'h264',
                           no_segmentation: bool = False) -> Dict[str, Any]:
    """Полная обработка видео файла: сжатие, извлечение аудио, транскрипция"""
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            return {'errors': [f"Видео файл не найден: {video_path}"]}
            
        print(f"🚀 Начинаю полную обработку видео: {video_path.name}")
        print(f"📁 Папка: {video_path.parent}")
        
        # Получаем размер файла
        file_size = video_path.stat().st_size
        print(f"📊 Размер: {file_size / (1024*1024):.1f} MB")
        
        results = {
            'video_compressed': False,
            'audio_extracted': False,
            'transcript_created': False,
            'files_created': [],
            'errors': []
        }
        
        # Шаг 1: Сжатие видео
        video_output_path = video_path.parent / f"{video_path.stem}_compressed.mp4"
        
        if video_output_path.exists() and "compressed" in video_output_path.name:
            print(f"⏭️ Сжатое видео уже существует: {video_output_path.name}")
            results['video_compressed'] = True
        else:
            try:
                compress_video(str(video_path), str(video_output_path), quality, codec)
                results['video_compressed'] = True
                results['files_created'].append(str(video_output_path))
                print(f"✅ Видео сжато: {video_output_path.name}")
            except Exception as e:
                error_msg = f"Ошибка сжатия видео: {e}"
                print(f"❌ {error_msg}")
                results['errors'].append(error_msg)
                return results
        
        # Шаг 2: Извлечение аудио
        audio_output_path = video_path.parent / f"{video_path.stem}_compressed.{audio_format}"
        
        if audio_output_path.exists():
            print(f"⏭️ Аудио файл уже существует: {audio_output_path.name}")
            results['audio_extracted'] = True
        else:
            try:
                extract_audio(str(video_output_path), str(audio_output_path), quality)
                results['audio_extracted'] = True
                results['files_created'].append(str(audio_output_path))
                print(f"✅ Аудио извлечено: {audio_output_path.name}")
            except Exception as e:
                error_msg = f"Ошибка извлечения аудио: {e}"
                print(f"❌ {error_msg}")
                results['errors'].append(error_msg)
                return results
        
        # Шаг 3: Транскрипция аудио
        print(f"🎤 Транскрипция аудио: {audio_output_path.name}")
        
        if audio_output_path.exists():
            try:
                transcript_output_name = f"{video_path.stem}_transcript.md"
                transcript_output_path = video_path.parent / transcript_output_name
                
                # Инициализируем AudioProcessor
                audio_processor = AudioProcessor()
                
                # Обрабатываем аудио (с сегментацией или без)
                if no_segmentation:
                    # Транскрипция без сегментации
                    result = audio_processor.process_audio_file_full(str(audio_output_path), 'md')
                else:
                    # Обычная обработка с сегментацией
                    result = audio_processor.process_audio_file(str(audio_output_path), 'md')
                
                if result and result.get('speakers'):
                    # Сохраняем транскрипт в нужную папку
                    with open(transcript_output_path, 'w', encoding='utf-8') as f:
                        f.write(f"# Транскрипция: {audio_output_path.name}\n\n")
                        f.write(f"**Файл:** {audio_output_path.name}\n")
                        f.write(f"**Размер:** {result.get('file_size', 0)} байт\n")
                        f.write(f"**Длительность:** {result.get('total_duration', 0)} мс\n")
                        f.write(f"**Сегментов:** {result.get('total_segments', 0)}\n")
                        f.write(f"**Участников:** {len(result.get('speakers', {}))}\n")
                        f.write(f"**Обработано:** {result.get('processed_at', '')}\n\n")
                        f.write("---\n\n")
                        
                        for speaker, segments in result['speakers'].items():
                            f.write(f"## {speaker}\n\n")
                            for seg in segments:
                                start_s = seg['start_time'] / 1000
                                end_s = seg['end_time'] / 1000
                                f.write(f"**[{start_s:.1f}s - {end_s:.1f}s]** {seg['text']}\n\n")
                    
                    results['transcript_created'] = True
                    results['files_created'].append(str(transcript_output_path))
                    print(f"✅ Транскрипт создан: {transcript_output_name}")
                else:
                    results['errors'].append("Ошибка транскрипции")
                    
            except Exception as e:
                error_msg = f"Ошибка транскрипции: {e}"
                print(f"❌ {error_msg}")
                results['errors'].append(error_msg)
        else:
            if transcript_output_path.exists():
                print(f"⏭️ Транскрипт уже существует: {transcript_output_name}")
                results['transcript_created'] = True
            else:
                print(f"⚠️ Аудио файл не найден для транскрипции")
        
        # Итоговая статистика
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"🎬 Видео сжато: {'✅' if results['video_compressed'] else '❌'}")
        print(f"🎵 Аудио извлечено: {'✅' if results['audio_extracted'] else '❌'}")
        print(f"📝 Транскрипт создан: {'✅' if results['transcript_created'] else '❌'}")
        
        if results['files_created']:
            print(f"📁 Создано файлов: {len(results['files_created'])}")
            for file_path in results['files_created']:
                print(f"   📄 {Path(file_path).name}")
        
        if results['errors']:
            print(f"❌ Ошибки: {len(results['errors'])}")
            for error in results['errors']:
                print(f"   ⚠️ {error}")
        
        return results
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        return {'errors': [str(e)]}

def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Полная обработка видео файла')
    parser.add_argument('video_path', help='Путь к видео файлу')
    parser.add_argument('--format', choices=['mp3', 'wav', 'm4a'], default='mp3',
                       help='Формат выходного аудио')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество обработки')
    parser.add_argument('--codec', choices=['h264', 'h265', 'vp9'], default='h264',
                       help='Кодек для сжатия видео')
    parser.add_argument('--no-segmentation', action='store_true',
                       help='Транскрипция без сегментации (все слова в одном абзаце)')
    
    args = parser.parse_args()
    
    # Проверяем наличие ffmpeg
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ ffmpeg не найден. Установите ffmpeg для обработки видео.")
        sys.exit(1)
    
    # Запускаем обработку
    results = process_video_full_flow(
        args.video_path, 
        args.format, 
        args.quality, 
        args.codec,
        args.no_segmentation
    )
    
    if results.get('errors'):
        sys.exit(1)

if __name__ == "__main__":
    main()
