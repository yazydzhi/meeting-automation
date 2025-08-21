#!/usr/bin/env python3
"""
Детальный тест Google Drive API для личного и рабочего аккаунтов
Проверяет различные scopes и операции с подробной диагностикой
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

# Загружаем переменные окружения
load_dotenv()

# Различные Drive scopes для тестирования
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
    'https://www.googleapis.com/auth/drive.appdata',
    'https://www.googleapis.com/auth/drive.photos.readonly'
]

def print_section(title, char="=", width=80):
    """Печатает красивый разделитель"""
    print(f"\n{char * width}")
    print(f"🎯 {title}")
    print(f"{char * width}")

def analyze_token_detailed(token_path, account_name):
    """Детальный анализ токена"""
    print(f"\n🔍 Детальный анализ токена {account_name}:")
    print(f"📁 Файл: {token_path}")
    
    if not os.path.exists(token_path):
        print("❌ Файл токена не найден")
        return None
    
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        print("✅ Токен успешно прочитан")
        
        # Основная информация
        print(f"\n📋 Основная информация:")
        print(f"  Client ID: {token_data.get('client_id', 'N/A')}")
        print(f"  Account: {token_data.get('account', 'N/A')}")
        print(f"  Token Type: {token_data.get('token_type', 'N/A')}")
        print(f"  Universe Domain: {token_data.get('universe_domain', 'N/A')}")
        
        # Время истечения
        expiry = token_data.get('expiry')
        if expiry:
            try:
                expiry_time = datetime.fromisoformat(expiry.replace('Z', '+00:00'))
                now = datetime.now(expiry_time.tzinfo)
                time_left = expiry_time - now
                
                if time_left.total_seconds() > 0:
                    hours_left = time_left.total_seconds() / 3600
                    print(f"  ⏰ Истекает через: {hours_left:.1f} часов")
                else:
                    print(f"  ⚠️ Токен истек: {abs(time_left.total_seconds() / 3600):.1f} часов назад")
            except:
                print(f"  Expiry: {expiry}")
        
        # Области доступа
        print(f"\n🎯 Области доступа (scopes):")
        scopes = token_data.get('scopes', [])
        if isinstance(scopes, str):
            scopes = scopes.split(' ')
        
        if scopes:
            for i, scope in enumerate(scopes, 1):
                if scope.strip():
                    scope_name = scope.split('/')[-1]
                    print(f"  {i}. {scope_name}")
                    print(f"     {scope}")
        else:
            print("  ⚠️ Scopes не найдены")
        
        # Анализ типов scopes
        calendar_scopes = [s for s in scopes if 'calendar' in s]
        drive_scopes = [s for s in scopes if 'drive' in s]
        other_scopes = [s for s in scopes if 'calendar' not in s and 'drive' not in s]
        
        print(f"\n📊 Анализ scopes:")
        print(f"  📅 Calendar scopes: {len(calendar_scopes)}")
        print(f"  📁 Drive scopes: {len(drive_scopes)}")
        print(f"  🔧 Другие scopes: {len(other_scopes)}")
        
        if drive_scopes:
            print(f"\n✅ Найденные Drive scopes:")
            for scope in drive_scopes:
                scope_name = scope.split('/')[-1]
                print(f"    ✅ {scope_name}")
        else:
            print(f"\n❌ Drive scopes НЕ найдены в токене!")
        
        return token_data
        
    except Exception as e:
        print(f"❌ Ошибка чтения токена: {e}")
        return None

def get_drive_service_with_scope(oauth_client_path, token_path, scope, account_name):
    """Создает Drive сервис с конкретным scope"""
    try:
        creds = None
        
        # Загружаем существующий токен
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, [scope])
        
        # Проверяем валидность
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                print(f"    ✅ Токен обновлен для {scope}")
            else:
                # Создаем новый токен
                flow = InstalledAppFlow.from_client_secrets_file(oauth_client_path, [scope])
                creds = flow.run_local_server(port=0)
                print(f"    ✅ Новый токен создан для {scope}")
                
                # Сохраняем
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
        
        # Создаем сервис
        service = build('drive', 'v3', credentials=creds)
        print(f"    ✅ Drive сервис создан с scope: {scope.split('/')[-1]}")
        return service
        
    except Exception as e:
        print(f"    ❌ Ошибка создания сервиса: {e}")
        return None

def test_drive_operations(service, scope, account_name):
    """Тестирует различные операции Drive API"""
    scope_name = scope.split('/')[-1]
    print(f"\n  🧪 Тестируем операции с scope: {scope_name}")
    
    results = {
        'user_info': False,
        'file_list': False,
        'folder_create': False,
        'file_upload': False,
        'permissions': False
    }
    
    try:
        # Тест 1: Информация о пользователе
        print(f"    📋 Тест 1: Информация о пользователе...")
        about = service.about().get(fields="user,storageQuota").execute()
        user_info = about.get('user', {})
        storage = about.get('storageQuota', {})
        
        print(f"      ✅ Пользователь: {user_info.get('displayName', 'N/A')}")
        print(f"      📧 Email: {user_info.get('emailAddress', 'N/A')}")
        
        if storage:
            used = int(storage.get('usage', 0))
            limit = int(storage.get('limit', 0))
            if limit > 0:
                used_gb = used / (1024**3)
                limit_gb = limit / (1024**3)
                percent_used = (used / limit) * 100
                print(f"      💾 Хранилище: {used_gb:.2f} GB / {limit_gb:.2f} GB ({percent_used:.1f}%)")
        
        results['user_info'] = True
        
    except HttpError as e:
        print(f"      ❌ Ошибка получения информации: {e.status_code} - {e.reason}")
    except Exception as e:
        print(f"      ❌ Неожиданная ошибка: {e}")
    
    try:
        # Тест 2: Список файлов
        print(f"    📁 Тест 2: Список файлов...")
        files = service.files().list(
            pageSize=5,
            fields="files(id,name,mimeType,size,modifiedTime,owners)",
            orderBy="modifiedTime desc"
        ).execute()
        
        file_list = files.get('files', [])
        print(f"      ✅ Найдено файлов: {len(file_list)}")
        
        for i, file in enumerate(file_list[:3], 1):
            name = file.get('name', 'N/A')
            mime_type = file.get('mimeType', 'N/A')
            size = file.get('size', 'N/A')
            
            if size and size != 'N/A':
                size_mb = int(size) / (1024*1024)
                size_str = f"{size_mb:.2f} MB"
            else:
                size_str = "N/A"
            
            print(f"        {i}. {name}")
            print(f"           Type: {mime_type}, Size: {size_str}")
        
        results['file_list'] = True
        
    except HttpError as e:
        print(f"      ❌ Ошибка получения списка файлов: {e.status_code} - {e.reason}")
    except Exception as e:
        print(f"      ❌ Неожиданная ошибка: {e}")
    
    # Тест 3: Создание папки (только для записи)
    if 'readonly' not in scope_name and 'metadata' not in scope_name:
        try:
            print(f"    📂 Тест 3: Создание тестовой папки...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            folder_name = f"Test_{account_name}_{scope_name}_{timestamp}"
            
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            folder = service.files().create(body=folder_metadata, fields='id,name,webViewLink').execute()
            folder_id = folder.get('id')
            folder_link = folder.get('webViewLink', 'N/A')
            
            print(f"      ✅ Папка создана: {folder.get('name')}")
            print(f"      🔗 ID: {folder_id}")
            print(f"      🌐 Ссылка: {folder_link}")
            
            # Удаляем тестовую папку
            service.files().delete(fileId=folder_id).execute()
            print(f"      🗑️ Тестовая папка удалена")
            
            results['folder_create'] = True
            
        except HttpError as e:
            print(f"      ❌ Ошибка создания папки: {e.status_code} - {e.reason}")
        except Exception as e:
            print(f"      ❌ Неожиданная ошибка: {e}")
    else:
        print(f"    📂 Тест 3: Создание папки (пропущено - readonly scope)")
    
    return results

def test_account_drive(account_type, oauth_client_path, token_path):
    """Тестирует Drive API для одного аккаунта"""
    print_section(f"Тестирование Google Drive API - {account_type} аккаунт")
    
    # Анализируем токен
    token_data = analyze_token_detailed(token_path, account_type)
    if not token_data:
        return {}
    
    # Проверяем наличие OAuth client
    if not os.path.exists(oauth_client_path):
        print(f"❌ OAuth client не найден: {oauth_client_path}")
        return {}
    
    print(f"\n📋 OAuth Client: {os.path.basename(oauth_client_path)}")
    
    # Извлекаем project ID из client ID
    client_id = token_data.get('client_id', '')
    if client_id:
        project_id = client_id.split('-')[0]
        print(f"🏗️ Project ID: {project_id}")
    
    # Тестируем каждый scope
    results = {}
    
    for i, scope in enumerate(DRIVE_SCOPES, 1):
        scope_name = scope.split('/')[-1]
        
        print(f"\n{'─' * 80}")
        print(f"🎯 Тест {i}/{len(DRIVE_SCOPES)}: {scope_name}")
        print(f"📋 Scope: {scope}")
        print(f"{'─' * 80}")
        
        # Создаем сервис
        service = get_drive_service_with_scope(oauth_client_path, token_path, scope, account_type)
        
        if service:
            # Тестируем операции
            test_results = test_drive_operations(service, scope, account_type)
            results[scope] = test_results
        else:
            results[scope] = {
                'user_info': False,
                'file_list': False,
                'folder_create': False,
                'file_upload': False,
                'permissions': False
            }
    
    return results

def generate_drive_report(personal_results, work_results):
    """Генерирует детальный отчет по Drive API"""
    print_section("ДЕТАЛЬНЫЙ ОТЧЕТ ПО GOOGLE DRIVE API")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"📅 Время тестирования: {timestamp}")
    
    accounts = [
        ("Личный аккаунт", personal_results),
        ("Рабочий аккаунт", work_results)
    ]
    
    for account_name, results in accounts:
        print(f"\n🎯 {account_name}:")
        
        if not results:
            print("  ❌ Тестирование не проведено (ошибка конфигурации)")
            continue
        
        # Подсчитываем статистику
        total_scopes = len(results)
        working_scopes = 0
        partially_working = 0
        
        for scope, scope_results in results.items():
            scope_name = scope.split('/')[-1]
            working_operations = sum(scope_results.values())
            total_operations = len(scope_results)
            
            if working_operations == total_operations:
                status = "✅ ПОЛНОСТЬЮ РАБОТАЕТ"
                working_scopes += 1
            elif working_operations > 0:
                status = f"⚠️ ЧАСТИЧНО РАБОТАЕТ ({working_operations}/{total_operations})"
                partially_working += 1
            else:
                status = "❌ НЕ РАБОТАЕТ"
            
            print(f"  📁 {scope_name}: {status}")
            
            # Детали операций
            if working_operations > 0:
                for operation, success in scope_results.items():
                    if success:
                        print(f"    ✅ {operation}")
        
        # Общая статистика
        print(f"\n  📊 Статистика {account_name}:")
        print(f"    ✅ Полностью работающих scopes: {working_scopes}/{total_scopes}")
        print(f"    ⚠️ Частично работающих scopes: {partially_working}/{total_scopes}")
        print(f"    ❌ Не работающих scopes: {total_scopes - working_scopes - partially_working}/{total_scopes}")
    
    # Общие выводы
    print(f"\n💡 Выводы и рекомендации:")
    
    personal_working = any(any(scope_results.values()) for scope_results in personal_results.values()) if personal_results else False
    work_working = any(any(scope_results.values()) for scope_results in work_results.values()) if work_results else False
    
    if personal_working and work_working:
        print("  🎉 Drive API работает для обоих аккаунтов!")
        print("  🚀 Система готова к полному использованию")
    elif personal_working or work_working:
        working_account = "личного" if personal_working else "рабочего"
        not_working_account = "рабочего" if personal_working else "личного"
        print(f"  ✅ Drive API работает для {working_account} аккаунта")
        print(f"  🔧 Нужно настроить Drive API для {not_working_account} аккаунта")
    else:
        print("  ❌ Drive API не работает ни для одного аккаунта")
        print("  🔧 Необходимо включить Google Drive API в обоих проектах:")
        print("    - Личный проект (testapp-68416)")
        print("    - Рабочий проект (948812030960)")

def main():
    """Основная функция"""
    print("🚀 ДЕТАЛЬНЫЙ ТЕСТ GOOGLE DRIVE API")
    print("🎯 Тестируем личный и рабочий аккаунты")
    print("📁 Все Drive scopes + детальная диагностика")
    
    # Получаем переменные окружения
    personal_oauth = os.getenv('PERSONAL_GOOGLE_OAUTH_CLIENT')
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    
    work_oauth = os.getenv('WORK_GOOGLE_OAUTH_CLIENT')
    work_token = os.getenv('WORK_GOOGLE_TOKEN')
    
    # Проверяем переменные
    missing_vars = []
    if not personal_oauth:
        missing_vars.append('PERSONAL_GOOGLE_OAUTH_CLIENT')
    if not personal_token:
        missing_vars.append('PERSONAL_GOOGLE_TOKEN')
    if not work_oauth:
        missing_vars.append('WORK_GOOGLE_OAUTH_CLIENT')
    if not work_token:
        missing_vars.append('WORK_GOOGLE_TOKEN')
    
    if missing_vars:
        print(f"❌ Не найдены переменные окружения: {', '.join(missing_vars)}")
        return
    
    # Тестируем аккаунты
    personal_results = test_account_drive("Личный", personal_oauth, personal_token)
    work_results = test_account_drive("Рабочий", work_oauth, work_token)
    
    # Генерируем отчет
    generate_drive_report(personal_results, work_results)
    
    print(f"\n{'=' * 80}")
    print("🎊 Детальное тестирование Drive API завершено!")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    main()
