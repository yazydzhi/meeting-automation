#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест альтернативных провайдеров календаря и Google Drive
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, 'src')

try:
    from calendar_alternatives import get_calendar_provider, CalendarEvent
    from drive_alternatives import get_drive_provider, DriveFile
    from config_manager import ConfigManager, create_sample_env
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def test_config_manager():
    """Тестируем менеджер конфигурации."""
    print("🔧 Тестируем менеджер конфигурации...")
    
    # Создаем пример .env файла
    create_sample_env()
    print("✅ Создан .env.sample файл")
    
    # Загружаем конфигурацию
    config = ConfigManager()
    print("\n📋 Текущая конфигурация:")
    print(config.get_config_summary())
    
    # Проверяем валидность
    if config.validate_config():
        print("✅ Конфигурация корректна")
    else:
        print("❌ Конфигурация содержит ошибки")
    
    return config

def test_calendar_providers():
    """Тестируем различные провайдеры календаря."""
    print("\n📅 Тестируем провайдеры календаря...")
    
    # Тестируем Google Calendar API
    print("\n🎯 Google Calendar API:")
    try:
        provider = get_calendar_provider('google_api', 
                                       credentials_path='creds/client_secret.json',
                                       calendar_id='primary')
        events = provider.get_today_events()
        print(f"   ✅ Событий на сегодня: {len(events)}")
        for event in events[:3]:  # Показываем первые 3
            print(f"      - {event.title} ({event.start.strftime('%H:%M')})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем Notion
    print("\n🎯 Notion календарь:")
    try:
        provider = get_calendar_provider('notion',
                                       notion_token=os.getenv('NOTION_TOKEN', ''),
                                       database_id=os.getenv('NOTION_DATABASE_ID', ''))
        events = provider.get_upcoming_events(days=7)
        print(f"   ✅ Событий на неделю: {len(events)}")
        for event in events[:3]:
            print(f"      - {event.title} ({event.start.strftime('%Y-%m-%d %H:%M')})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем веб-календарь (iCal)
    print("\n🎯 Веб-календарь (iCal):")
    try:
        # Используем публичный календарь для теста
        test_url = "https://calendar.google.com/calendar/ical/ru.russian%23holiday%40group.v.calendar.google.com/public/basic.ics"
        provider = get_calendar_provider('web_ical', calendar_url=test_url)
        events = provider.get_upcoming_events(days=30)
        print(f"   ✅ Событий на месяц: {len(events)}")
        for event in events[:3]:
            print(f"      - {event.title} ({event.start.strftime('%Y-%m-%d')})")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем локальный JSON календарь
    print("\n🎯 Локальный JSON календарь:")
    try:
        # Создаем тестовый JSON файл
        test_events = {
            "events": [
                {
                    "title": "Тестовая встреча 1",
                    "start": "2025-08-22T10:00:00",
                    "end": "2025-08-22T11:00:00",
                    "description": "Описание тестовой встречи",
                    "location": "Онлайн",
                    "attendees": ["user1@example.com", "user2@example.com"],
                    "meeting_link": "https://meet.google.com/test"
                },
                {
                    "title": "Тестовая встреча 2",
                    "start": "2025-08-23T14:00:00",
                    "end": "2025-08-23T15:00:00",
                    "description": "Вторая тестовая встреча",
                    "location": "Офис",
                    "attendees": ["user3@example.com"],
                    "meeting_link": ""
                }
            ]
        }
        
        test_file = "data/calendar/test_events.json"
        os.makedirs(os.path.dirname(test_file), exist_ok=True)
        
        import json
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(test_events, f, ensure_ascii=False, indent=2)
        
        provider = get_calendar_provider('local_json', calendar_file=test_file)
        events = provider.get_upcoming_events(days=7)
        print(f"   ✅ Событий на неделю: {len(events)}")
        for event in events:
            print(f"      - {event.title} ({event.start.strftime('%Y-%m-%d %H:%M')})")
            print(f"        Участники: {', '.join(event.attendees)}")
            print(f"        Источник: {event.calendar_source}")
        
        # Очистка
        os.remove(test_file)
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def test_drive_providers():
    """Тестируем различные провайдеры Google Drive."""
    print("\n💾 Тестируем провайдеры Google Drive...")
    
    # Тестируем Google Drive API
    print("\n🎯 Google Drive API:")
    try:
        provider = get_drive_provider('google_api',
                                    credentials_path='creds/client_secret.json')
        files = provider.list_files()
        print(f"   ✅ Файлов в корне: {len(files)}")
        for file in files[:3]:
            print(f"      - {file.name} ({file.mime_type}, {file.size} байт)")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем локальный провайдер
    print("\n🎯 Локальный провайдер:")
    try:
        provider = get_drive_provider('local', root_path='data/test_local_drive')
        
        # Создаем тестовые файлы
        test_dir = Path('data/test_local_drive')
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем тестовый файл
        test_file = test_dir / 'test.txt'
        with open(test_file, 'w') as f:
            f.write('Тестовый файл для проверки локального провайдера')
        
        # Создаем тестовую папку
        test_folder = test_dir / 'test_folder'
        test_folder.mkdir(exist_ok=True)
        
        # Создаем файл в папке
        nested_file = test_folder / 'nested.txt'
        with open(nested_file, 'w') as f:
            f.write('Файл в вложенной папке')
        
        # Тестируем список файлов
        files = provider.list_files()
        print(f"   ✅ Файлов в корне: {len(files)}")
        for file in files:
            print(f"      - {file.name} ({file.mime_type}, {file.size} байт)")
            print(f"        MD5: {file.md5_hash}")
            print(f"        Локальный путь: {file.local_path}")
        
        # Тестируем создание папки
        new_folder_id = provider.create_folder('new_test_folder')
        print(f"   ✅ Создана папка: {new_folder_id}")
        
        # Тестируем загрузку файла
        upload_result = provider.upload_file('data/test_local_drive/test.txt', 
                                           'new_test_folder', 'uploaded_test.txt')
        print(f"   ✅ Файл загружен: {upload_result}")
        
        # Тестируем проверку существования
        exists = provider.file_exists('uploaded_test.txt', 'new_test_folder')
        print(f"   ✅ Файл существует: {exists}")
        
        # Очистка
        import shutil
        shutil.rmtree('data/test_local_drive')
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    
    # Тестируем Google Drive для Desktop
    print("\n🎯 Google Drive для Desktop:")
    try:
        # Проверяем, есть ли настроенный путь
        desktop_path = os.getenv('GOOGLE_DRIVE_DESKTOP_PATH', '')
        if desktop_path and os.path.exists(desktop_path):
            provider = get_drive_provider('google_desktop', drive_path=desktop_path)
            files = provider.list_files()
            print(f"   ✅ Файлов в Google Drive: {len(files)}")
            for file in files[:3]:
                print(f"      - {file.name} ({file.mime_type}, {file.size} байт)")
        else:
            print("   ⚠️ Путь Google Drive для Desktop не настроен")
            
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

def test_integration():
    """Тестируем интеграцию провайдеров."""
    print("\n🔗 Тестируем интеграцию провайдеров...")
    
    try:
        # Создаем тестовое событие
        test_event = CalendarEvent(
            title="Интеграционный тест",
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=1),
            description="Тест интеграции провайдеров",
            location="Тестовая среда",
            attendees=["test@example.com"],
            meeting_link="https://test.com",
            calendar_source="test"
        )
        
        print(f"✅ Создано тестовое событие: {test_event.title}")
        print(f"   Время: {test_event.start.strftime('%Y-%m-%d %H:%M')} - {test_event.end.strftime('%H:%M')}")
        print(f"   Участники: {', '.join(test_event.attendees)}")
        print(f"   Источник: {test_event.calendar_source}")
        
        # Создаем тестовый файл
        test_file = DriveFile(
            name="test_integration.txt",
            file_id="test_123",
            mime_type="text/plain",
            size=1024,
            modified_time=datetime.now(),
            parents=[],
            web_view_link="file://test",
            local_path="/tmp/test.txt",
            md5_hash="test_hash"
        )
        
        print(f"\n✅ Создан тестовый файл: {test_file.name}")
        print(f"   MIME тип: {test_file.mime_type}")
        print(f"   Размер: {test_file.size} байт")
        print(f"   MD5: {test_file.md5_hash}")
        
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")

def main():
    """Основная функция тестирования."""
    print("🚀 Тест альтернативных провайдеров календаря и Google Drive")
    print("=" * 70)
    
    # Тестируем менеджер конфигурации
    config = test_config_manager()
    
    # Тестируем провайдеры календаря
    test_calendar_providers()
    
    # Тестируем провайдеры Google Drive
    test_drive_providers()
    
    # Тестируем интеграцию
    test_integration()
    
    print("\n" + "=" * 70)
    print("✅ Тестирование завершено!")
    print("\n📝 Следующие шаги:")
    print("1. Настройте .env файл с нужными провайдерами")
    print("2. Укажите CALENDAR_PROVIDER и DRIVE_PROVIDER")
    print("3. Настройте параметры для выбранных провайдеров")
    print("4. Запустите основной скрипт с новой конфигурацией")

if __name__ == "__main__":
    main()
