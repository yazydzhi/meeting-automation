#!/usr/bin/env python3
"""
Комплексный тест всех Google API для личного и рабочего аккаунтов
Проверяет доступ к Calendar и Drive API с различными scope
"""

import os
import sys
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Scope для Google APIs
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

def print_section(title, char="="):
    """Печатает красивый разделитель для секций"""
    print(f"\n{char * 80}")
    print(f"🎯 {title}")
    print(f"{char * 80}")

def analyze_token(token_path, account_name):
    """Анализирует содержимое токена"""
    print(f"\n🔍 Анализ токена {account_name}: {token_path}")
    
    if not os.path.exists(token_path):
        print("❌ Файл токена не найден")
        return None
    
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        print("✅ Токен прочитан успешно")
        print(f"  Client ID: {token_data.get('client_id', 'N/A')}")
        print(f"  Account: {token_data.get('account', 'N/A')}")
        print(f"  Expiry: {token_data.get('expiry', 'N/A')}")
        print(f"  Области доступа:")
        
        scopes = token_data.get('scopes', [])
        if isinstance(scopes, str):
            scopes = scopes.split(' ')
        
        for scope in scopes:
            if scope.strip():
                print(f"    - {scope}")
        
        # Проверяем наличие различных scopes
        calendar_scopes = [s for s in scopes if 'calendar' in s]
        drive_scopes = [s for s in scopes if 'drive' in s]
        
        print(f"  🗓️ Calendar scopes: {len(calendar_scopes)}")
        print(f"  📁 Drive scopes: {len(drive_scopes)}")
        
        return token_data
        
    except Exception as e:
        print(f"❌ Ошибка анализа токена: {e}")
        return None

def get_service(oauth_client_path, token_path, scopes, service_name, version):
    """Получает сервис Google API"""
    if not os.path.exists(oauth_client_path):
        print(f"❌ OAuth client не найден: {oauth_client_path}")
        return None
    
    creds = None
    
    # Проверяем существующий токен
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
        except Exception as e:
            print(f"❌ Ошибка загрузки токена: {e}")
            return None
    
    # Если нет валидного токена, создаем новый
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                print("✅ Токен обновлен")
            except Exception as e:
                print(f"❌ Ошибка обновления токена: {e}")
                creds = None
        
        if not creds:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_path, scopes)
                creds = flow.run_local_server(port=0)
                print("✅ Новый токен создан")
            except Exception as e:
                print(f"❌ Ошибка создания токена: {e}")
                return None
        
        # Сохраняем токен
        try:
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            print(f"✅ Токен сохранен")
        except Exception as e:
            print(f"❌ Ошибка сохранения токена: {e}")
    
    try:
        service = build(service_name, version, credentials=creds)
        print(f"✅ {service_name.title()} сервис создан")
        return service
    except Exception as e:
        print(f"❌ Ошибка создания {service_name} сервиса: {e}")
        return None

def test_calendar_api(service, account_name):
    """Тестирует Calendar API"""
    print(f"\n📅 Тестируем Calendar API для {account_name}...")
    
    try:
        # Получаем список календарей
        calendars = service.calendarList().list().execute()
        calendar_list = calendars.get('items', [])
        print(f"  ✅ Найдено календарей: {len(calendar_list)}")
        
        # Показываем первые 3 календаря
        for i, calendar in enumerate(calendar_list[:3]):
            print(f"    {i+1}. {calendar.get('summary', 'N/A')} ({calendar.get('id', 'N/A')})")
        
        # Получаем события из основного календаря
        primary_calendar = calendar_list[0] if calendar_list else None
        if primary_calendar:
            events = service.events().list(
                calendarId=primary_calendar['id'],
                maxResults=5,
                singleEvents=True,
                orderBy='startTime',
                timeMin=datetime.utcnow().isoformat() + 'Z'
            ).execute()
            
            event_list = events.get('items', [])
            print(f"  ✅ Найдено предстоящих событий: {len(event_list)}")
            
            for i, event in enumerate(event_list[:3]):
                title = event.get('summary', 'Без названия')
                start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', 'N/A'))
                print(f"    {i+1}. {title} ({start})")
        
        return True
        
    except HttpError as e:
        print(f"  ❌ Ошибка Calendar API: {e.status_code} - {e.reason}")
        return False
    except Exception as e:
        print(f"  ❌ Неожиданная ошибка Calendar API: {e}")
        return False

def test_drive_api(service, account_name, scope_name):
    """Тестирует Drive API"""
    print(f"\n📁 Тестируем Drive API для {account_name} (scope: {scope_name})...")
    
    try:
        # Тест 1: Получение информации о пользователе
        print("  📋 Тест 1: Информация о пользователе...")
        about = service.about().get(fields="user,storageQuota").execute()
        user_info = about.get('user', {})
        storage = about.get('storageQuota', {})
        
        print(f"    ✅ Пользователь: {user_info.get('displayName', 'N/A')} ({user_info.get('emailAddress', 'N/A')})")
        
        used = int(storage.get('usage', 0))
        limit = int(storage.get('limit', 0))
        if limit > 0:
            used_gb = used / (1024**3)
            limit_gb = limit / (1024**3)
            print(f"    📊 Хранилище: {used_gb:.1f} GB / {limit_gb:.1f} GB")
        
        # Тест 2: Список файлов (ограниченный)
        print("  📁 Тест 2: Список файлов...")
        files = service.files().list(
            pageSize=10, 
            fields="files(id,name,mimeType,modifiedTime)",
            orderBy="modifiedTime desc"
        ).execute()
        
        file_list = files.get('files', [])
        print(f"    ✅ Найдено файлов: {len(file_list)}")
        
        for i, file in enumerate(file_list[:3]):
            name = file.get('name', 'N/A')
            mime_type = file.get('mimeType', 'N/A')
            modified = file.get('modifiedTime', 'N/A')
            print(f"      {i+1}. {name} ({mime_type}) - {modified}")
        
        # Тест 3: Создание тестовой папки (только для записи)
        if 'readonly' not in scope_name:
            print("  📂 Тест 3: Создание тестовой папки...")
            folder_metadata = {
                'name': f'Test_{account_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = service.files().create(body=folder_metadata, fields='id,name').execute()
            folder_id = folder.get('id')
            print(f"    ✅ Папка создана: {folder.get('name')} (ID: {folder_id})")
            
            # Удаляем тестовую папку
            service.files().delete(fileId=folder_id).execute()
            print(f"    ✅ Тестовая папка удалена")
        else:
            print("  📂 Тест 3: Создание папки (пропущено - readonly scope)")
        
        return True
        
    except HttpError as e:
        error_details = e.error_details[0] if e.error_details else {}
        print(f"    ❌ Ошибка Drive API: {e.status_code} - {e.reason}")
        print(f"      Детали: {error_details}")
        return False
    except Exception as e:
        print(f"    ❌ Неожиданная ошибка Drive API: {e}")
        return False

def test_account(account_type, oauth_client_path, token_path, calendar_id):
    """Тестирует один аккаунт (личный или рабочий)"""
    print_section(f"Тестирование {account_type} аккаунта", "=")
    
    results = {
        'account_type': account_type,
        'calendar_api': False,
        'drive_scopes': {}
    }
    
    # Анализируем токен
    token_data = analyze_token(token_path, account_type)
    
    # Тестируем Calendar API
    print(f"\n📅 Тестируем Google Calendar API...")
    calendar_service = get_service(oauth_client_path, token_path, CALENDAR_SCOPES, 'calendar', 'v3')
    if calendar_service:
        results['calendar_api'] = test_calendar_api(calendar_service, account_type)
    
    # Тестируем Drive API с разными scopes
    print(f"\n📁 Тестируем Google Drive API...")
    for scope in DRIVE_SCOPES:
        print(f"\n{'─' * 60}")
        print(f"🔍 Scope: {scope}")
        print(f"{'─' * 60}")
        
        drive_service = get_service(oauth_client_path, token_path, [scope], 'drive', 'v3')
        if drive_service:
            success = test_drive_api(drive_service, account_type, scope)
            results['drive_scopes'][scope] = success
        else:
            results['drive_scopes'][scope] = False
    
    return results

def generate_report(personal_results, work_results):
    """Генерирует итоговый отчет"""
    print_section("ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ", "=")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Общая статистика
    print(f"\n📊 Общая статистика (на {timestamp}):")
    
    accounts = [
        ("Личный аккаунт", personal_results),
        ("Рабочий аккаунт", work_results)
    ]
    
    for account_name, results in accounts:
        print(f"\n🎯 {account_name}:")
        
        # Calendar API
        calendar_status = "✅ РАБОТАЕТ" if results['calendar_api'] else "❌ НЕ РАБОТАЕТ"
        print(f"  📅 Calendar API: {calendar_status}")
        
        # Drive API scopes
        drive_working = [s for s, r in results['drive_scopes'].items() if r]
        drive_total = len(results['drive_scopes'])
        
        if drive_working:
            print(f"  📁 Drive API: ✅ РАБОТАЕТ ({len(drive_working)}/{drive_total} scopes)")
            for scope in drive_working:
                scope_short = scope.split('/')[-1]
                print(f"    ✅ {scope_short}")
        else:
            print(f"  📁 Drive API: ❌ НЕ РАБОТАЕТ (0/{drive_total} scopes)")
            for scope in results['drive_scopes'].keys():
                scope_short = scope.split('/')[-1]
                print(f"    ❌ {scope_short}")
    
    # Рекомендации
    print(f"\n💡 Рекомендации:")
    
    all_calendar_working = personal_results['calendar_api'] and work_results['calendar_api']
    any_drive_working = any(personal_results['drive_scopes'].values()) or any(work_results['drive_scopes'].values())
    
    if all_calendar_working and any_drive_working:
        print("  🎉 Отлично! Все основные API работают.")
        print("  🚀 Система готова к полноценному использованию!")
    elif all_calendar_working:
        print("  ✅ Calendar API работает для обоих аккаунтов.")
        print("  🔧 Нужно включить Google Drive API в проектах:")
        if not any(personal_results['drive_scopes'].values()):
            print("    - Личный проект (testapp-68416)")
        if not any(work_results['drive_scopes'].values()):
            print("    - Рабочий проект (948812030960)")
        print("  📋 Система готова к базовому использованию (Calendar + Notion)")
    else:
        print("  ⚠️ Есть проблемы с API, требуется диагностика.")
    
    # Статус готовности
    calendar_ready = 50 if all_calendar_working else 0
    drive_ready = 50 if any_drive_working else 0
    total_ready = calendar_ready + drive_ready
    
    print(f"\n📈 Готовность системы: {total_ready}%")
    print(f"  📅 Calendar API: {calendar_ready}%")
    print(f"  📁 Drive API: {drive_ready}%")

def main():
    """Основная функция тестирования"""
    print("🚀 КОМПЛЕКСНЫЙ ТЕСТ ВСЕХ GOOGLE API")
    print("🎯 Тестируем личный и рабочий аккаунты")
    print("📅 Calendar API + 📁 Drive API")
    
    # Получаем переменные окружения
    personal_oauth = os.getenv('PERSONAL_GOOGLE_OAUTH_CLIENT')
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    personal_calendar = os.getenv('PERSONAL_CALENDAR_ID')
    
    work_oauth = os.getenv('WORK_GOOGLE_OAUTH_CLIENT')
    work_token = os.getenv('WORK_GOOGLE_TOKEN')
    work_calendar = os.getenv('WORK_CALENDAR_ID')
    
    # Проверяем наличие переменных
    if not all([personal_oauth, personal_token, personal_calendar]):
        print("❌ Ошибка: Не все переменные для личного аккаунта найдены")
        return
    
    if not all([work_oauth, work_token, work_calendar]):
        print("❌ Ошибка: Не все переменные для рабочего аккаунта найдены")
        return
    
    # Тестируем аккаунты
    personal_results = test_account("Личный", personal_oauth, personal_token, personal_calendar)
    work_results = test_account("Рабочий", work_oauth, work_token, work_calendar)
    
    # Генерируем отчет
    generate_report(personal_results, work_results)
    
    print(f"\n{'=' * 80}")
    print("🎊 Тестирование завершено!")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
