#!/usr/bin/env python3
"""
Получение токена для личного Google Drive API
Создает новый токен с Drive scopes
"""

import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Расширенные scopes для Drive API
DRIVE_SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',  # Calendar (существующий)
    'https://www.googleapis.com/auth/drive',              # Полный доступ к Drive
    'https://www.googleapis.com/auth/drive.file',         # Доступ к файлам приложения
    'https://www.googleapis.com/auth/drive.readonly'      # Только чтение Drive
]

def print_section(title, char="="):
    """Печатает красивый разделитель"""
    print(f"\n{char * 80}")
    print(f"🎯 {title}")
    print(f"{char * 80}")

def check_current_token():
    """Проверяет текущий токен личного аккаунта"""
    print("🔍 Проверяем текущий токен личного аккаунта...")
    
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    if not personal_token:
        print("❌ Переменная PERSONAL_GOOGLE_TOKEN не найдена")
        return None
    
    if not os.path.exists(personal_token):
        print(f"❌ Файл токена не найден: {personal_token}")
        return None
    
    try:
        with open(personal_token, 'r') as f:
            import json
            token_data = json.load(f)
        
        print("✅ Токен найден и прочитан")
        print(f"  📁 Файл: {personal_token}")
        
        if 'scopes' in token_data:
            scopes = token_data['scopes']
            if isinstance(scopes, str):
                scopes = scopes.split(' ')
            
            print(f"  📋 Текущие scopes ({len(scopes)}):")
            for scope in scopes:
                if scope.strip():
                    scope_name = scope.split('/')[-1]
                    print(f"    - {scope_name}")
            
            # Проверяем наличие Drive scopes
            drive_scopes = [s for s in scopes if 'drive' in s]
            calendar_scopes = [s for s in scopes if 'calendar' in s]
            
            print(f"  🎯 Анализ:")
            print(f"    📅 Calendar scopes: {len(calendar_scopes)}")
            print(f"    📁 Drive scopes: {len(drive_scopes)}")
            
            if drive_scopes:
                print("  ✅ Drive scopes уже есть в токене!")
                return token_data
            else:
                print("  ❌ Drive scopes отсутствуют - нужен новый токен")
                return None
        else:
            print("  ⚠️ Токен без scopes")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка чтения токена: {e}")
        return None

def backup_current_token():
    """Создает резервную копию текущего токена"""
    print("\n💾 Создаем резервную копию текущего токена...")
    
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    if not personal_token or not os.path.exists(personal_token):
        print("  ⚠️ Токен для резервного копирования не найден")
        return False
    
    try:
        import shutil
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{personal_token}.backup_{timestamp}"
        
        shutil.copy2(personal_token, backup_path)
        print(f"  ✅ Резервная копия создана: {backup_path}")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка создания резервной копии: {e}")
        return False

def create_new_drive_token():
    """Создает новый токен с Drive scopes"""
    print("\n🔑 Создаем новый токен с Drive scopes...")
    
    personal_oauth = os.getenv('PERSONAL_GOOGLE_OAUTH_CLIENT')
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    
    if not personal_oauth:
        print("❌ Переменная PERSONAL_GOOGLE_OAUTH_CLIENT не найдена")
        return False
    
    if not os.path.exists(personal_oauth):
        print(f"❌ OAuth client не найден: {personal_oauth}")
        return False
    
    try:
        print(f"  📁 OAuth Client: {os.path.basename(personal_oauth)}")
        print(f"  🎯 Запрашиваем scopes:")
        for scope in DRIVE_SCOPES:
            scope_name = scope.split('/')[-1]
            print(f"    - {scope_name}")
        
        print(f"\n  🌐 Открывается браузер для авторизации...")
        print(f"  📋 Войдите в личный Google аккаунт и предоставьте права доступа")
        
        # Создаем flow для авторизации
        flow = InstalledAppFlow.from_client_secrets_file(personal_oauth, DRIVE_SCOPES)
        creds = flow.run_local_server(port=0)
        
        print(f"  ✅ Авторизация успешна!")
        
        # Сохраняем новый токен
        if personal_token:
            with open(personal_token, 'w') as token:
                token.write(creds.to_json())
            print(f"  💾 Новый токен сохранен: {personal_token}")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка создания токена: {e}")
        return False

def test_drive_access():
    """Тестирует доступ к Drive API с новым токеном"""
    print("\n🧪 Тестируем доступ к Drive API...")
    
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    if not personal_token or not os.path.exists(personal_token):
        print("❌ Токен не найден для тестирования")
        return False
    
    try:
        # Загружаем токен
        creds = Credentials.from_authorized_user_file(personal_token, DRIVE_SCOPES)
        
        # Создаем Drive сервис
        service = build('drive', 'v3', credentials=creds)
        print("  ✅ Drive сервис создан")
        
        # Тест 1: Информация о пользователе
        print("  📋 Тест 1: Информация о пользователе...")
        about = service.about().get(fields="user,storageQuota").execute()
        user_info = about.get('user', {})
        
        print(f"    ✅ Пользователь: {user_info.get('displayName', 'N/A')}")
        print(f"    📧 Email: {user_info.get('emailAddress', 'N/A')}")
        
        # Тест 2: Список файлов
        print("  📁 Тест 2: Список файлов...")
        files = service.files().list(pageSize=5, fields="files(id,name,mimeType)").execute()
        file_list = files.get('files', [])
        print(f"    ✅ Найдено файлов: {len(file_list)}")
        
        # Тест 3: Создание тестовой папки
        print("  📂 Тест 3: Создание тестовой папки...")
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        folder_metadata = {
            'name': f'Test_Drive_Access_{timestamp}',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = service.files().create(body=folder_metadata, fields='id,name,webViewLink').execute()
        folder_id = folder.get('id')
        folder_link = folder.get('webViewLink', 'N/A')
        
        print(f"    ✅ Папка создана: {folder.get('name')}")
        print(f"    🔗 ID: {folder_id}")
        print(f"    🌐 Ссылка: {folder_link}")
        
        # Удаляем тестовую папку
        service.files().delete(fileId=folder_id).execute()
        print(f"    🗑️ Тестовая папка удалена")
        
        print("  🎉 Все тесты Drive API прошли успешно!")
        return True
        
    except HttpError as e:
        if e.status_code == 403:
            print(f"    ❌ Нет доступа к Drive API: {e.reason}")
            print(f"    💡 Возможно, Drive API не включен в проекте")
            return False
        else:
            print(f"    ❌ Ошибка Drive API: {e.status_code} - {e.reason}")
            return False
    except Exception as e:
        print(f"    ❌ Неожиданная ошибка: {e}")
        return False

def test_calendar_access():
    """Тестирует доступ к Calendar API с новым токеном"""
    print("\n📅 Тестируем доступ к Calendar API...")
    
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    if not personal_token or not os.path.exists(personal_token):
        print("❌ Токен не найден для тестирования")
        return False
    
    try:
        # Загружаем токен
        creds = Credentials.from_authorized_user_file(personal_token, DRIVE_SCOPES)
        
        # Создаем Calendar сервис
        service = build('calendar', 'v3', credentials=creds)
        print("  ✅ Calendar сервис создан")
        
        # Получаем список календарей
        calendars = service.calendarList().list(maxResults=5).execute()
        calendar_list = calendars.get('items', [])
        
        print(f"  ✅ Найдено календарей: {len(calendar_list)}")
        
        # Показываем первый календарь
        if calendar_list:
            primary = calendar_list[0]
            print(f"    📅 Основной: {primary.get('summary', 'N/A')}")
        
        print("  🎉 Calendar API работает отлично!")
        return True
        
    except Exception as e:
        print(f"    ❌ Ошибка Calendar API: {e}")
        return False

def main():
    """Основная функция получения Drive токена"""
    print("🚀 ПОЛУЧЕНИЕ ТОКЕНА ДЛЯ ЛИЧНОГО GOOGLE DRIVE API")
    print("🎯 Создаем новый токен с расширенными правами")
    
    # Проверяем текущий токен
    current_token = check_current_token()
    
    if current_token and any('drive' in s for s in current_token.get('scopes', [])):
        print("\n✅ Drive scopes уже есть в токене!")
        print("💡 Токен готов к использованию")
        return
    
    # Создаем резервную копию
    backup_created = backup_current_token()
    
    # Создаем новый токен
    print_section("СОЗДАНИЕ НОВОГО ТОКЕНА")
    
    if create_new_drive_token():
        print("\n✅ Новый токен создан успешно!")
        
        # Тестируем доступ
        print_section("ТЕСТИРОВАНИЕ ДОСТУПА")
        
        drive_ok = test_drive_access()
        calendar_ok = test_calendar_access()
        
        if drive_ok and calendar_ok:
            print("\n🎉 Отлично! Новый токен работает для Drive и Calendar!")
            print("💡 Теперь у вас есть полный доступ к Google API")
        elif calendar_ok:
            print("\n⚠️ Calendar работает, но Drive API недоступен")
            print("💡 Нужно включить Google Drive API в Cloud Console")
        else:
            print("\n❌ Есть проблемы с доступом к API")
            print("💡 Проверьте настройки в Google Cloud Console")
    else:
        print("\n❌ Не удалось создать новый токен")
        if backup_created:
            print("💡 Резервная копия создана, можно восстановить старый токен")
    
    print(f"\n{'=' * 80}")
    print("🎊 Процесс получения Drive токена завершен!")

if __name__ == '__main__':
    main()
