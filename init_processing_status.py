#!/usr/bin/env python3
"""
Скрипт для инициализации файлов статуса обработки во всех папках.
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

from processing_status import ProcessingStatus

def init_all_processing_status():
    """Инициализируем статус обработки для всех папок."""
    
    # Основные папки для проверки
    base_paths = [
        "/Users/azg/Downloads/01 - yazydzhi@gmail.com",
        "/Users/azg/Downloads/02 - work@company.com"
    ]
    
    for base_path in base_paths:
        base_path_obj = Path(base_path)
        if not base_path_obj.exists():
            print(f"⚠️ Базовая папка не найдена: {base_path}")
            continue
            
        print(f"\n🔍 Проверяем папку: {base_path}")
        
        # Получаем все подпапки
        try:
            subfolders = [f for f in base_path_obj.iterdir() if f.is_dir()]
            print(f"📁 Найдено подпапок: {len(subfolders)}")
            
            for subfolder in subfolders:
                print(f"\n📂 Обрабатываем подпапку: {subfolder.name}")
                
                # Инициализируем статус для подпапки
                status = ProcessingStatus(str(subfolder))
                
                # Проверяем, есть ли уже файлы в папке
                video_files = list(subfolder.glob("*.mov")) + list(subfolder.glob("*.mp4")) + list(subfolder.glob("*.avi"))
                audio_files = list(subfolder.glob("*.mp3")) + list(subfolder.glob("*.wav"))
                
                print(f"   🎬 Видео файлы: {len(video_files)}")
                print(f"   🎵 Аудио файлы: {len(audio_files)}")
                
                # Если есть видео файлы, добавляем их в отслеживание
                for video_file in video_files:
                    if 'compressed' not in video_file.name.lower():
                        print(f"   📝 Добавляем в отслеживание: {video_file.name}")
                        status.add_file(str(video_file), 'video')
                        
                        # Проверяем, есть ли уже сжатые версии
                        compressed_video = subfolder / f"{video_file.stem}_compressed.mp4"
                        compressed_audio = subfolder / f"{video_file.stem}_compressed.mp3"
                        
                        # Проверяем все необходимые этапы
                        video_processed = compressed_video.exists()
                        audio_processed = compressed_audio.exists()
                        
                        # Сначала добавляем все этапы
                        if video_processed:
                            print(f"      ✅ Сжатое видео уже существует: {compressed_video.name}")
                            # Просто отмечаем, что этап уже существует, не добавляем его
                            print(f"      ⏭️ Этап video_compression уже существует")
                        
                        if audio_processed:
                            print(f"      ✅ Аудио файл уже существует: {compressed_audio.name}")
                            status.mark_file_processed(
                                video_file.name, 
                                'audio_extraction',
                                [str(compressed_audio)]
                            )
                        else:
                            print(f"      ❌ Аудио файл не найден - файл частично обработан")
                            # Отмечаем этап как неудачный, чтобы система знала, что нужно повторить
                            status.mark_file_failed(
                                video_file.name,
                                'audio_extraction',
                                'Аудио файл не найден - возможно, исходное видео не содержит аудио'
                            )
                            
                        # Проверяем наличие транскрипции
                        transcript_files = list(subfolder.glob("*.txt")) + list(subfolder.glob("*.md")) + list(subfolder.glob("*.csv"))
                        transcript_processed = any('transcript' in f.name.lower() or 'transcription' in f.name.lower() for f in transcript_files)
                        
                        if transcript_processed:
                            print(f"      ✅ Транскрипция найдена")
                            status.mark_file_processed(
                                video_file.name, 
                                'transcription',
                                [str(f) for f in transcript_files if 'transcript' in f.name.lower() or 'transcription' in f.name.lower()]
                            )
                        else:
                            print(f"      ❌ Транскрипция не найдена")
                            status.mark_file_failed(
                                video_file.name,
                                'transcription',
                                'Файлы транскрипции не найдены'
                            )
                        
                        # Принудительно обновляем статус файла
                        status.update_file_status(video_file.name)
                        
                        # Теперь проверяем итоговый статус
                        current_status = status.get_file_status(video_file.name)
                        if current_status:
                            print(f"      📊 Итоговый статус: {current_status['status']}")
                            
                        if video_processed and audio_processed and transcript_processed:
                            print(f"      ✅ Файл полностью обработан")
                        elif video_processed:
                            print(f"      🔄 Файл частично обработан (только видео)")
                        else:
                            print(f"      ❌ Файл не обработан")
                    else:
                        print(f"   ⏭️ Пропускаем уже сжатый файл: {video_file.name}")
                
                # Выводим итоговую сводку
                status.print_summary()
                
        except Exception as e:
            print(f"❌ Ошибка обработки папки {base_path}: {e}")

if __name__ == "__main__":
    init_all_processing_status()
