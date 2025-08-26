#!/usr/bin/env python3
"""
Скрипт для проверки всех папок и установки корректного статуса обработки.
Переименовывает старые файлы статуса в новые стандартные названия.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from typing import Dict, List, Any

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.processing_status import ProcessingStatus
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта")
    sys.exit(1)


def find_old_status_files(root_path: str) -> List[Dict[str, Any]]:
    """Найти все старые файлы статуса в проекте."""
    old_files = []
    
    for root, dirs, files in os.walk(root_path):
        for file in files:
            if file == "📊 processing_status.json" or file == "📊 СТАТУС ОБРАБОТКИ.txt":
                old_files.append({
                    'path': os.path.join(root, file),
                    'old_name': file,
                    'new_name': 'processing_status.json' if file.endswith('.json') else 'processing_status.md',
                    'folder': root
                })
    
    return old_files


def rename_status_files(old_files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Переименовать старые файлы статуса в новые."""
    renamed_files = []
    
    for file_info in old_files:
        old_path = file_info['path']
        new_name = file_info['new_name']
        new_path = os.path.join(file_info['folder'], new_name)
        
        try:
            # Если новый файл уже существует, создаем резервную копию
            if os.path.exists(new_path):
                backup_path = f"{new_path}.backup"
                shutil.move(new_path, backup_path)
                print(f"📋 Создана резервная копия: {backup_path}")
            
            # Переименовываем файл
            shutil.move(old_path, new_path)
            print(f"✅ Переименован: {file_info['old_name']} → {new_name}")
            
            file_info['new_path'] = new_path
            renamed_files.append(file_info)
            
        except Exception as e:
            print(f"❌ Ошибка переименования {old_path}: {e}")
    
    return renamed_files


def update_processing_status(folder_path: str) -> bool:
    """Обновить статус обработки для папки."""
    try:
        status_manager = ProcessingStatus(folder_path)
        
        # Проверяем, есть ли файлы для обработки
        video_files = []
        audio_files = []
        transcript_files = []
        
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            if os.path.isfile(file_path):
                if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.wmv')):
                    video_files.append(file)
                elif file.lower().endswith(('.mp3', '.wav', '.m4a', '.aac')):
                    audio_files.append(file)
                elif file.endswith('_transcript.txt'):
                    transcript_files.append(file)
        
        # Обновляем статус для каждого файла
        for video_file in video_files:
            if not status_manager.is_file_processed(video_file, 'video_compression'):
                status_manager.add_file(video_file, 'video')
                print(f"📹 Добавлен видео файл: {video_file}")
        
        for audio_file in audio_files:
            if not status_manager.is_file_processed(audio_file, 'audio_extraction'):
                status_manager.add_file(audio_file, 'audio')
                print(f"🎵 Добавлен аудио файл: {audio_file}")
        
        for transcript_file in transcript_files:
            if not status_manager.is_file_processed(transcript_file, 'transcription'):
                status_manager.add_file(transcript_file, 'transcript')
                print(f"📝 Добавлена транскрипция: {transcript_file}")
        
        # Обновляем общий статус папки
        status_manager.get_summary()
        print(f"✅ Статус обновлен для папки: {folder_path}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка обработки {folder_path}: {e}")
        return False


def process_all_folders(config_manager: ConfigManager) -> Dict[str, Any]:
    """Обработать все папки аккаунтов."""
    results = {
        'personal': {'status': 'skipped', 'folders': 0, 'errors': 0},
        'work': {'status': 'skipped', 'folders': 0, 'errors': 0},
        'total_folders': 0,
        'total_errors': 0
    }
    
    # Обрабатываем личный аккаунт
    if config_manager.is_personal_enabled():
        personal_config = config_manager.get_personal_config()
        personal_folder = personal_config.get('local_drive_root')
        
        if personal_folder and os.path.exists(personal_folder):
            print(f"👤 Обрабатываю личный аккаунт: {personal_folder}")
            results['personal']['status'] = 'processing'
            
            try:
                # Обрабатываем подпапки событий
                for event_folder in os.listdir(personal_folder):
                    event_path = os.path.join(personal_folder, event_folder)
                    if os.path.isdir(event_path):
                        results['personal']['folders'] += 1
                        results['total_folders'] += 1
                        
                        if update_processing_status(event_path):
                            print(f"  ✅ {event_folder}")
                        else:
                            results['personal']['errors'] += 1
                            results['total_errors'] += 1
                            print(f"  ❌ {event_folder}")
                
                results['personal']['status'] = 'completed'
                
            except Exception as e:
                print(f"❌ Ошибка обработки личного аккаунта: {e}")
                results['personal']['status'] = 'error'
                results['personal']['errors'] += 1
                results['total_errors'] += 1
    
    # Обрабатываем рабочий аккаунт
    if config_manager.is_work_enabled():
        work_config = config_manager.get_work_config()
        work_folder = work_config.get('local_drive_root')
        
        if work_folder and os.path.exists(work_folder):
            print(f"🏢 Обрабатываю рабочий аккаунт: {work_folder}")
            results['work']['status'] = 'processing'
            
            try:
                # Обрабатываем подпапки событий
                for event_folder in os.listdir(work_folder):
                    event_path = os.path.join(work_folder, event_folder)
                    if os.path.isdir(event_path):
                        results['work']['folders'] += 1
                        results['total_folders'] += 1
                        
                        if update_processing_status(event_path):
                            print(f"  ✅ {event_folder}")
                        else:
                            results['work']['errors'] += 1
                            results['total_errors'] += 1
                            print(f"  ❌ {event_folder}")
                
                results['work']['status'] = 'completed'
                
            except Exception as e:
                print(f"❌ Ошибка обработки рабочего аккаунта: {e}")
                results['work']['status'] = 'error'
                results['work']['errors'] += 1
                results['total_errors'] += 1
    
    return results


def main():
    """Основная функция."""
    print("🔍 Скрипт проверки папок и обновления статуса обработки")
    print("=" * 60)
    
    # Загружаем конфигурацию
    try:
        config_manager = ConfigManager()
        print("✅ Конфигурация загружена")
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        sys.exit(1)
    
    # Проверяем конфигурацию
    if not config_manager.validate_config():
        print("❌ Конфигурация некорректна")
        sys.exit(1)
    
    print("\n📁 Поиск старых файлов статуса...")
    
    # Ищем старые файлы статуса
    old_files = find_old_status_files('.')
    
    if old_files:
        print(f"📋 Найдено {len(old_files)} старых файлов статуса:")
        for file_info in old_files:
            print(f"  - {file_info['path']}")
        
        print("\n🔄 Переименование файлов...")
        renamed_files = rename_status_files(old_files)
        print(f"✅ Переименовано {len(renamed_files)} файлов")
    else:
        print("✅ Старые файлы статуса не найдены")
    
    print("\n📊 Обновление статуса обработки для всех папок...")
    
    # Обрабатываем все папки
    results = process_all_folders(config_manager)
    
    print("\n📊 Результаты обработки:")
    print(f"  👤 Личный аккаунт: {results['personal']['status']} ({results['personal']['folders']} папок, {results['personal']['errors']} ошибок)")
    print(f"  🏢 Рабочий аккаунт: {results['work']['status']} ({results['work']['folders']} папок, {results['work']['errors']} ошибок)")
    print(f"  📁 Всего папок: {results['total_folders']}")
    print(f"  ❌ Всего ошибок: {results['total_errors']}")
    
    if results['total_errors'] == 0:
        print("\n🎉 Все папки обработаны успешно!")
    else:
        print(f"\n⚠️ Обработано с ошибками: {results['total_errors']} папок")


if __name__ == "__main__":
    main()
