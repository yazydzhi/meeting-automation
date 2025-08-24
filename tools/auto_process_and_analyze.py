#!/usr/bin/env python3
"""
Автоматическая обработка видео файлов с полным пайплайном:
1. Сжатие видео
2. Извлечение аудио в MP3
3. Транскрибация аудио
4. Анализ транскрипта через OpenAI
5. Добавление результатов в Notion
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.audio_processor import AudioProcessor
from src.transcript_analyzer import TranscriptAnalyzer
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

def transcribe_audio(audio_path: str, output_dir: Path, config: ConfigManager) -> Optional[Dict[str, Any]]:
    """Транскрибирует аудио файл."""
    try:
        print(f"📝 Транскрибация аудио {os.path.basename(audio_path)}...")
        
        # Инициализируем AudioProcessor
        audio_processor = AudioProcessor(config)
        
        # Транскрибируем без сегментации для лучшего качества
        result = audio_processor.process_audio_file(audio_path, 'md')
        
        if result and result.get('speakers'):
            # Сохраняем транскрипт
            transcript_name = Path(audio_path).stem + "_transcript.md"
            transcript_path = output_dir / transcript_name
            
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"# Транскрипция: {os.path.basename(audio_path)}\n\n")
                f.write(f"**Файл:** {os.path.basename(audio_path)}\n")
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
            
            print(f"✅ Транскрипт создан: {transcript_name}")
            return {
                'transcript_path': str(transcript_path),
                'result': result
            }
        else:
            print(f"❌ Ошибка транскрибации")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка транскрибации: {e}")
        return None

def analyze_transcript_and_create_notion(transcript_path: str, meeting_title: str, meeting_date: str, config: ConfigManager) -> Optional[Dict[str, Any]]:
    """Анализирует транскрипт и создает данные для Notion."""
    try:
        print(f"🔍 Анализ транскрипта через OpenAI...")
        
        # Читаем транскрипт
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        # Инициализируем TranscriptAnalyzer
        api_key = config.config.get('openai', {}).get('api_key')
        model = config.config.get('openai', {}).get('analysis_model', 'gpt-4o-mini')
        
        if not api_key:
            print("❌ OpenAI API ключ не найден в конфигурации")
            return None
        
        analyzer = TranscriptAnalyzer(api_key, model)
        
        # Анализируем транскрипт
        analysis_result = analyzer.analyze_meeting_transcript(
            transcript_text,
            meeting_title,
            meeting_date
        )
        
        if analysis_result:
            # Сохраняем результат анализа
            analysis_file = transcript_path.replace('_transcript.md', '_analysis.json')
            if analyzer.save_analysis_to_file(analysis_result, analysis_file):
                print(f"✅ Анализ сохранен: {os.path.basename(analysis_file)}")
            
            # Создаем данные для Notion
            notion_data = analyzer.create_notion_page_data(analysis_result)
            if notion_data:
                notion_file = transcript_path.replace('_transcript.md', '_notion_data.json')
                import json
                with open(notion_file, 'w', encoding='utf-8') as f:
                    json.dump(notion_data, f, ensure_ascii=False, indent=2)
                print(f"✅ Данные для Notion созданы: {os.path.basename(notion_file)}")
            
            return {
                'analysis_result': analysis_result,
                'notion_data': notion_data,
                'analysis_file': analysis_file,
                'notion_file': notion_file
            }
        else:
            print("❌ Не удалось проанализировать транскрипт")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка анализа транскрипта: {e}")
        return None

def auto_process_video_full_flow(video_path: str, meeting_title: str, meeting_date: str, 
                                config_file: str = 'env.work', quality: str = 'medium', 
                                codec: str = 'h264') -> Dict[str, Any]:
    """Полный автоматический пайплайн обработки видео."""
    
    results = {
        'video_compressed': False,
        'audio_extracted': False,
        'transcript_created': False,
        'analysis_completed': False,
        'notion_data_created': False,
        'files_created': [],
        'errors': []
    }
    
    try:
        # Загружаем конфигурацию
        config = ConfigManager(config_file)
        
        # Проверяем наличие ffmpeg
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            error_msg = "ffmpeg не найден. Установите ffmpeg для обработки видео."
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results
        
        video_path = Path(video_path)
        if not video_path.exists():
            error_msg = f"Видео файл не найден: {video_path}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results
        
        # Проверяем, не является ли файл уже обработанным
        if 'compressed' in video_path.name.lower():
            error_msg = f"Файл уже обработан: {video_path.name}"
            print(f"❌ {error_msg}")
            results['errors'].append(error_msg)
            return results
        
        output_dir = video_path.parent
        
        # 1. Сжимаем видео
        video_output_name = video_path.stem + "_compressed.mp4"
        video_output_path = output_dir / video_output_name
        
        if not video_output_path.exists():
            if compress_video(str(video_path), str(video_output_path), quality, codec):
                results['video_compressed'] = True
                results['files_created'].append(str(video_output_path))
            else:
                results['errors'].append("Ошибка сжатия видео")
        else:
            print(f"⏭️ Сжатое видео уже существует: {video_output_name}")
            results['video_compressed'] = True
        
        # 2. Извлекаем аудио
        audio_output_name = video_path.stem + "_compressed.mp3"
        audio_output_path = output_dir / audio_output_name
        
        if not audio_output_path.exists():
            # Пытаемся извлечь аудио из исходного файла
            if extract_audio(str(video_path), str(audio_output_path), quality):
                results['audio_extracted'] = True
                results['files_created'].append(str(audio_output_path))
            else:
                # Если не удалось, пробуем из сжатого видео
                if results['video_compressed']:
                    print(f"🔄 Пробуем извлечь аудио из сжатого видео...")
                    if extract_audio(str(video_output_path), str(audio_output_path), quality):
                        results['audio_extracted'] = True
                        results['files_created'].append(str(audio_output_path))
                    else:
                        results['errors'].append("Ошибка извлечения аудио из исходного и сжатого видео")
                else:
                    results['errors'].append("Ошибка извлечения аудио")
        else:
            print(f"⏭️ Аудио файл уже существует: {audio_output_name}")
            results['audio_extracted'] = True
        
        # 3. Транскрибируем аудио
        transcript_name = video_path.stem + "_transcript.md"
        transcript_path = output_dir / transcript_name
        
        if not transcript_path.exists() and results['audio_extracted']:
            transcript_result = transcribe_audio(str(audio_output_path), output_dir, config)
            if transcript_result:
                results['transcript_created'] = True
                results['files_created'].append(transcript_result['transcript_path'])
            else:
                results['errors'].append("Ошибка транскрибации")
        elif transcript_path.exists():
            print(f"⏭️ Транскрипт уже существует: {transcript_name}")
            results['transcript_created'] = True
        else:
            print(f"⚠️ Аудио файл не найден для транскрибации")
        
        # 4. Анализируем транскрипт и создаем данные для Notion
        if results['transcript_created'] and meeting_title and meeting_date:
            analysis_result = analyze_transcript_and_create_notion(
                str(transcript_path), meeting_title, meeting_date, config
            )
            if analysis_result:
                results['analysis_completed'] = True
                results['notion_data_created'] = True
                results['files_created'].extend([
                    analysis_result['analysis_file'],
                    analysis_result['notion_file']
                ])
            else:
                results['errors'].append("Ошибка анализа транскрипта")
        
        # Итоговая статистика
        print(f"\n📊 ИТОГОВАЯ СТАТИСТИКА:")
        print(f"🎬 Видео сжато: {'✅' if results['video_compressed'] else '❌'}")
        print(f"🎵 Аудио извлечено: {'✅' if results['audio_extracted'] else '❌'}")
        print(f"📝 Транскрипт создан: {'✅' if results['transcript_created'] else '❌'}")
        print(f"🔍 Анализ завершен: {'✅' if results['analysis_completed'] else '❌'}")
        print(f"📋 Данные для Notion: {'✅' if results['notion_data_created'] else '❌'}")
        
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
        error_msg = f"Критическая ошибка: {e}"
        print(f"❌ {error_msg}")
        results['errors'].append(error_msg)
        return results

def main():
    """Основная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Автоматическая обработка видео с полным пайплайном')
    parser.add_argument('video_path', help='Путь к видео файлу')
    parser.add_argument('--title', required=True, help='Название встречи для анализа')
    parser.add_argument('--date', required=True, help='Дата встречи (YYYY-MM-DD)')
    parser.add_argument('--config', default='env.work', help='Файл конфигурации')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество обработки')
    parser.add_argument('--codec', choices=['h264', 'h265'], default='h264',
                       help='Кодек для сжатия видео')
    
    args = parser.parse_args()
    
    # Запускаем полный пайплайн
    results = auto_process_video_full_flow(
        args.video_path,
        args.title,
        args.date,
        args.config,
        args.quality,
        args.codec
    )
    
    if results.get('errors'):
        print(f"\n❌ Обработка завершена с ошибками")
        sys.exit(1)
    else:
        print(f"\n✅ Обработка завершена успешно!")

if __name__ == "__main__":
    main()
