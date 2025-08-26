#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки компрессии видео
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем src в путь
sys.path.insert(0, 'src')

try:
    from media_processor import get_media_processor
    from drive_sync import get_drive_sync
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def get_google_services(env):
    """Получает Google сервисы."""
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    
    # Scopes для личного аккаунта
    SCOPES = [
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file",
    ]
    
    creds = None
    
    # Проверяем существующий токен
    if os.path.exists('tokens/personal_token.json'):
        creds = Credentials.from_authorized_user_file('tokens/personal_token.json', SCOPES)
    
    # Если нет валидных кредов, запрашиваем авторизацию
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'creds/client_secret.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Сохраняем креды
        os.makedirs('tokens', exist_ok=True)
        with open('tokens/personal_token.json', 'w') as token:
            token.write(creds.to_json())
    
    # Создаем сервисы
    calendar_service = build('calendar', 'v3', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return calendar_service, drive_service

def test_video_compression():
    """Тестирует компрессию видео."""
    load_dotenv()
    
    try:
        # Получаем Google сервисы
        print("🔍 Получаем Google сервисы...")
        cal_svc, drive_svc = get_google_services({})
        
        if not drive_svc:
            print("❌ Google Drive сервис недоступен")
            return
        
        print("✅ Google Drive сервис доступен")
        
        # Проверяем переменные окружения
        parent_id = os.getenv('PERSONAL_DRIVE_PARENT_ID')
        sync_root = os.getenv('MEDIA_SYNC_ROOT', 'data/synced')
        
        if not parent_id:
            print("❌ PERSONAL_DRIVE_PARENT_ID не найден в .env")
            return
        
        print(f"📁 PERSONAL_DRIVE_PARENT_ID: {parent_id}")
        print(f"📁 MEDIA_SYNC_ROOT: {sync_root}")
        
        # Создаем синхронизатор и процессор с компрессией видео
        print("\n🔧 Создаем модули с компрессией видео...")
        drive_sync = get_drive_sync(drive_svc, sync_root)
        
        # Тестируем разные настройки компрессии
        compression_configs = [
            ("H.264 Medium", True, "medium", "h264"),
            ("H.264 High", True, "high", "h264"),
            ("H.265 Medium", True, "medium", "h265"),
            ("VP9 Medium", True, "medium", "vp9"),
        ]
        
        for config_name, compression, quality, codec in compression_configs:
            print(f"\n🎬 Тестируем конфигурацию: {config_name}")
            print(f"   Компрессия: {compression}, Качество: {quality}, Кодек: {codec}")
            
            media_processor = get_media_processor(
                drive_svc, 
                'mp3', 
                video_compression=compression,
                video_quality=quality,
                video_codec=codec
            )
            
            if not media_processor:
                print("❌ Не удалось создать модуль")
                continue
            
            print("✅ Модуль создан")
            
            # Ищем папки с событиями
            print(f"\n🔍 Ищем папки с событиями...")
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            folders_result = drive_svc.files().list(
                q=query,
                fields="files(id,name,createdTime)",
                orderBy="createdTime desc"
            ).execute()
            
            folders = folders_result.get("files", [])
            print(f"📁 Найдено папок: {len(folders)}")
            
            # Обрабатываем первую папку с видео
            for folder in folders[:1]:
                folder_id = folder['id']
                folder_name = folder['name']
                
                print(f"\n📁 Обрабатываем папку: {folder_name}")
                
                try:
                    # Синхронизируем папку
                    print(f"  🔄 Синхронизируем папку...")
                    sync_results = drive_sync.sync_folder(
                        folder_id, 
                        folder_name,
                        file_types=['video/*']
                    )
                    
                    print(f"  📊 Результаты синхронизации:")
                    print(f"    - Найдено файлов: {sync_results['files_found']}")
                    print(f"    - Синхронизировано: {sync_results['files_synced']}")
                    print(f"    - Пропущено: {sync_results['files_skipped']}")
                    print(f"    - Ошибки: {len(sync_results['errors'])}")
                    
                    if sync_results['files_synced'] > 0:
                        # Получаем локальный путь
                        local_path = drive_sync.get_local_path(folder_name)
                        print(f"  📁 Локальный путь: {local_path}")
                        
                        # Обрабатываем медиа файлы
                        print(f"  🎬 Обрабатываем медиа файлы...")
                        media_results = media_processor.process_folder(
                            folder_id, 
                            folder_name, 
                            local_path
                        )
                        
                        print(f"  📊 Результаты обработки:")
                        print(f"    - Найдено видео: {media_results['files_found']}")
                        print(f"    - Обработано: {media_results['files_processed']}")
                        print(f"    - Пропущено: {media_results['files_skipped']}")
                        print(f"    - Ошибки: {len(media_results['errors'])}")
                        print(f"    - Время обработки: {media_results['processing_time']:.2f} сек")
                        
                        # Если есть ошибки, показываем их
                        if media_results['errors']:
                            print(f"  ❌ Ошибки:")
                            for error in media_results['errors']:
                                print(f"    - {error}")
                        
                        break  # Обрабатываем только первую папку
                    
                except Exception as e:
                    print(f"  ❌ Ошибка обработки папки {folder_name}: {e}")
                    import traceback
                    traceback.print_exc()
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_video_compression()
