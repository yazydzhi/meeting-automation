#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки медиа обработки
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

def test_media_processing():
    """Тестирует медиа обработку."""
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
        
        # Создаем синхронизатор и процессор
        print("\n🔧 Создаем модули...")
        drive_sync = get_drive_sync(drive_svc, sync_root)
        media_processor = get_media_processor(drive_svc, 'mp3')
        
        if not drive_sync or not media_processor:
            print("❌ Не удалось создать модули")
            return
        
        print("✅ Модули созданы")
        
        # Ищем папки с событиями
        print("\n🔍 Ищем папки с событиями...")
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        folders_result = drive_svc.files().list(
            q=query,
            fields="files(id,name,createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        folders = folders_result.get("files", [])
        print(f"📁 Найдено папок: {len(folders)}")
        
        for folder in folders[:3]:  # Обрабатываем последние 3 папки
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
                    
                else:
                    print(f"  ⚠️ Файлы для синхронизации не найдены")
                    
            except Exception as e:
                print(f"  ❌ Ошибка обработки папки {folder_name}: {e}")
                import traceback
                traceback.print_exc()
        
        # Очистка старых файлов
        print(f"\n🧹 Очистка старых файлов...")
        cleanup_count = drive_sync.cleanup_old_files(7)  # 7 дней
        print(f"✅ Очищено {cleanup_count} старых файлов")
        
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_media_processing()
