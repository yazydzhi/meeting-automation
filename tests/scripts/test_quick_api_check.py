#!/usr/bin/env python3
"""
Быстрая проверка всех API
Простой тест для проверки доступности основных функций
"""

import os
import sys
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def test_notion_api():
    """Быстрый тест Notion API"""
    print("🔍 Тестируем Notion API...")
    
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("  ❌ Переменные Notion не найдены")
        return False
    
    try:
        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        
        # Проверяем доступ к базе данных
        url = f'https://api.notion.com/v1/databases/{database_id}'
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            db_info = response.json()
            title = db_info.get('title', [{}])[0].get('plain_text', 'N/A')
            print(f"  ✅ База данных: {title}")
            return True
        else:
            print(f"  ❌ Ошибка: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def test_google_calendar(oauth_client, token_path, account_name):
    """Быстрый тест Google Calendar"""
    print(f"📅 Тестируем Google Calendar ({account_name})...")
    
    try:
        if not os.path.exists(token_path):
            print(f"  ❌ Токен не найден: {token_path}")
            return False
        
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('calendar', 'v3', credentials=creds)
        
        # Получаем список календарей
        calendars = service.calendarList().list(maxResults=5).execute()
        calendar_count = len(calendars.get('items', []))
        
        print(f"  ✅ Найдено календарей: {calendar_count}")
        return True
        
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def test_google_drive(oauth_client, token_path, account_name):
    """Быстрый тест Google Drive"""
    print(f"📁 Тестируем Google Drive ({account_name})...")
    
    try:
        if not os.path.exists(token_path):
            print(f"  ❌ Токен не найден: {token_path}")
            return False
        
        creds = Credentials.from_authorized_user_file(token_path)
        service = build('drive', 'v3', credentials=creds)
        
        # Пробуем получить информацию о пользователе
        about = service.about().get(fields="user").execute()
        user = about.get('user', {})
        email = user.get('emailAddress', 'N/A')
        
        print(f"  ✅ Пользователь: {email}")
        return True
        
    except HttpError as e:
        if e.status_code == 403:
            print(f"  ❌ Нет доступа: API не включен или недостаточно прав")
        else:
            print(f"  ❌ Ошибка: {e.status_code} - {e.reason}")
        return False
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def check_environment_variables():
    """Проверяем переменные окружения"""
    print("🔍 Проверяем переменные окружения...")
    
    required_vars = [
        'NOTION_TOKEN',
        'NOTION_DATABASE_ID',
        'PERSONAL_GOOGLE_OAUTH_CLIENT',
        'PERSONAL_GOOGLE_TOKEN',
        'PERSONAL_CALENDAR_ID',
        'WORK_GOOGLE_OAUTH_CLIENT',
        'WORK_GOOGLE_TOKEN',
        'WORK_CALENDAR_ID'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"  ❌ Отсутствуют переменные: {', '.join(missing)}")
        return False
    else:
        print(f"  ✅ Все переменные найдены ({len(required_vars)})")
        return True

def main():
    """Основная функция быстрой проверки"""
    print("🚀 БЫСТРАЯ ПРОВЕРКА ВСЕХ API")
    print("=" * 50)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏰ Время: {timestamp}")
    
    results = {}
    
    # Проверяем переменные окружения
    env_ok = check_environment_variables()
    results['environment'] = env_ok
    
    if not env_ok:
        print("\n❌ Проверка остановлена из-за отсутствующих переменных")
        return
    
    print("\n" + "=" * 50)
    
    # Тестируем Notion
    results['notion'] = test_notion_api()
    
    # Тестируем Google Calendar
    personal_oauth = os.getenv('PERSONAL_GOOGLE_OAUTH_CLIENT')
    personal_token = os.getenv('PERSONAL_GOOGLE_TOKEN')
    work_oauth = os.getenv('WORK_GOOGLE_OAUTH_CLIENT')
    work_token = os.getenv('WORK_GOOGLE_TOKEN')
    
    results['calendar_personal'] = test_google_calendar(personal_oauth, personal_token, "Личный")
    results['calendar_work'] = test_google_calendar(work_oauth, work_token, "Рабочий")
    
    # Тестируем Google Drive
    results['drive_personal'] = test_google_drive(personal_oauth, personal_token, "Личный")
    results['drive_work'] = test_google_drive(work_oauth, work_token, "Рабочий")
    
    # Итоговый отчет
    print("\n" + "=" * 50)
    print("📊 ИТОГОВЫЙ ОТЧЕТ")
    print("=" * 50)
    
    services = [
        ("🔧 Переменные окружения", results['environment']),
        ("📋 Notion API", results['notion']),
        ("📅 Calendar (Личный)", results['calendar_personal']),
        ("📅 Calendar (Рабочий)", results['calendar_work']),
        ("📁 Drive (Личный)", results['drive_personal']),
        ("📁 Drive (Рабочий)", results['drive_work'])
    ]
    
    working_count = 0
    total_count = len(services)
    
    for service_name, status in services:
        status_text = "✅ РАБОТАЕТ" if status else "❌ НЕ РАБОТАЕТ"
        print(f"{service_name}: {status_text}")
        if status:
            working_count += 1
    
    # Общая статистика
    percentage = (working_count / total_count) * 100
    print(f"\n📈 Готовность системы: {working_count}/{total_count} ({percentage:.0f}%)")
    
    # Рекомендации
    print(f"\n💡 Рекомендации:")
    
    if working_count == total_count:
        print("  🎉 Все сервисы работают! Система готова к использованию.")
    elif results['notion'] and (results['calendar_personal'] or results['calendar_work']):
        print("  ✅ Основная функциональность работает (Calendar + Notion).")
        if not results['drive_personal'] and not results['drive_work']:
            print("  🔧 Для полной функциональности включите Google Drive API.")
    else:
        print("  ⚠️ Есть критические проблемы, требуется настройка.")
    
    print(f"\n{'=' * 50}")
    print("🎊 Быстрая проверка завершена!")

if __name__ == '__main__':
    main()
