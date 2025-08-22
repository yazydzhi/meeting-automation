#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отладки запросов к Google Drive API
"""

import os
from dotenv import load_dotenv
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

def debug_drive_queries():
    """Отлаживает запросы к Google Drive API."""
    load_dotenv()
    
    try:
        # Получаем Google сервисы
        print("🔍 Получаем Google сервисы...")
        cal_svc, drive_svc = get_google_services()
        print("✅ Google Drive сервис доступен")
        
        # Проверяем папки
        parent_id = os.getenv('PERSONAL_DRIVE_PARENT_ID')
        if not parent_id:
            print("❌ PERSONAL_DRIVE_PARENT_ID не найден в .env")
            return
        
        print(f"🔍 Ищем папки в родительской папке: {parent_id}")
        
        # Ищем папки
        query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        print(f"🔍 Запрос для папок: {query}")
        
        folders_result = drive_svc.files().list(
            q=query,
            fields="files(id,name,createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        folders = folders_result.get('files', [])
        print(f'📁 Найдено папок: {len(folders)}')
        
        for folder in folders:
            print(f'\n📁 Папка: {folder["name"]} (ID: {folder["id"]})')
            
            # Тест 1: Все файлы без фильтров
            print(f"  🔍 Тест 1: Все файлы без фильтров")
            files_query1 = f"'{folder['id']}' in parents and trashed=false"
            print(f"    Запрос: {files_query1}")
            
            files_result1 = drive_svc.files().list(
                q=files_query1,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files1 = files_result1.get('files', [])
            print(f"    📄 Найдено файлов: {len(files1)}")
            for file in files1:
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 0)
                size_str = f"{int(size):,} bytes" if size else "Unknown size"
                print(f"      📄 {file['name']} ({mime_type}, {size_str})")
            
            # Тест 2: Только видео файлы
            print(f"  🔍 Тест 2: Только видео файлы")
            files_query2 = f"'{folder['id']}' in parents and trashed=false and (mimeType='video/mp4' or mimeType='video/mkv' or mimeType='video/webm' or mimeType='video/avi' or mimeType='video/mov')"
            print(f"    Запрос: {files_query2}")
            
            files_result2 = drive_svc.files().list(
                q=files_query2,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files2 = files_result2.get('files', [])
            print(f"    🎬 Найдено видео файлов: {len(files2)}")
            for file in files2:
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 0)
                size_str = f"{int(size):,} bytes" if size else "Unknown size"
                print(f"      🎬 {file['name']} ({mime_type}, {size_str})")
            
            # Тест 3: По расширению файла
            print(f"  🔍 Тест 3: По расширению файла")
            files_query3 = f"'{folder['id']}' in parents and trashed=false and (name contains '.mp4' or name contains '.mkv' or name contains '.webm' or name contains '.avi' or name contains '.mov')"
            print(f"    Запрос: {files_query3}")
            
            files_result3 = drive_svc.files().list(
                q=files_query3,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files3 = files_result3.get('files', [])
            print(f"    🎬 Найдено файлов по расширению: {len(files3)}")
            for file in files3:
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 0)
                size_str = f"{int(size):,} bytes" if size else "Unknown size"
                print(f"      🎬 {file['name']} ({mime_type}, {size_str})")
            
            # Тест 4: Простой запрос video/*
            print(f"  🔍 Тест 4: Простой запрос video/*")
            files_query4 = f"'{folder['id']}' in parents and trashed=false and mimeType contains 'video/'"
            print(f"    Запрос: {files_query4}")
            
            files_result4 = drive_svc.files().list(
                q=files_query4,
                fields="files(id,name,mimeType,size,webViewLink)"
            ).execute()
            
            files4 = files_result4.get('files', [])
            print(f"    🎬 Найдено видео файлов (video/*): {len(files4)}")
            for file in files4:
                mime_type = file.get('mimeType', 'Unknown')
                size = file.get('size', 0)
                size_str = f"{int(size):,} bytes" if size else "Unknown size"
                print(f"      🎬 {file['name']} ({mime_type}, {size_str})")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_drive_queries()
