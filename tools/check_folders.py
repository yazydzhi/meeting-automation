#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки содержимого папок Google Drive
"""

import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes для личного аккаунта
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
]

def get_google_services():
    """Получает Google сервисы."""
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

def main():
    """Основная функция."""
    load_dotenv()
    
    try:
        # Получаем Google сервисы
        cal_svc, drive_svc = get_google_services()
        print("✅ Google сервисы подключены")
        
        # Проверяем папки
        parent_id = os.getenv('PERSONAL_DRIVE_PARENT_ID')
        if not parent_id:
            print("❌ PERSONAL_DRIVE_PARENT_ID не найден в .env")
            return
        
        print(f"🔍 Ищем папки в родительской папке: {parent_id}")
        
        # Ищем папки
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        folders_result = drive_svc.files().list(
            q=query,
            fields="files(id,name,createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        folders = folders_result.get('files', [])
        print(f'📁 Найдено папок: {len(folders)}')
        
        for folder in folders:
            print(f'\n📁 Папка: {folder["name"]} (ID: {folder["id"]})')
            
            # Проверяем содержимое папки
            files_query = f"'{folder['id']}' in parents and trashed=false"
            files_result = drive_svc.files().list(
                q=files_query,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files = files_result.get('files', [])
            print(f'  📄 Файлов в папке: {len(files)}')
            
            for file in files:
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 0)
                size_str = f"{int(size):,} bytes" if size else "Unknown size"
                print(f'    📄 {file["name"]} ({mime_type}, {size_str})')
                
                # Проверяем, является ли файл видео
                if mime_type.startswith('video/') or file["name"].lower().endswith(('.mp4', '.mkv', '.webm', '.avi', '.mov')):
                    print(f'      🎬 Это видео файл!')
        
        # Проверяем локальную синхронизацию
        print(f"\n🔍 Проверяем локальную синхронизацию...")
        sync_root = os.getenv('MEDIA_SYNC_ROOT', 'data/synced')
        
        if os.path.exists(sync_root):
            print(f"📁 Локальная директория: {sync_root}")
            for item in os.listdir(sync_root):
                item_path = os.path.join(sync_root, item)
                if os.path.isdir(item_path):
                    files_count = len([f for f in os.listdir(item_path) if os.path.isfile(os.path.join(item_path, f))])
                    print(f"  📁 {item}: {files_count} файлов")
                    
                    # Показываем файлы в папке
                    for file in os.listdir(item_path):
                        file_path = os.path.join(item_path, file)
                        if os.path.isfile(file_path):
                            size = os.path.getsize(file_path)
                            print(f"    📄 {file} ({size:,} bytes)")
        else:
            print(f"❌ Локальная директория {sync_root} не существует")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
