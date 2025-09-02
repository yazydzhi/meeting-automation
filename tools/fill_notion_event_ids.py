#!/usr/bin/env python3
"""
Скрипт для заполнения Event ID в страницах Notion на основе данных из SQLite.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def fill_notion_event_ids(dry_run=True):
    """Заполняет Event ID в страницах Notion."""
    
    # Получаем токен из переменных окружения
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("❌ Не найдены переменные окружения NOTION_TOKEN или NOTION_DATABASE_ID")
        return False
    
    try:
        # Настраиваем заголовки для API
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        print("🔧 Заполнение Event ID в страницах Notion...")
        print("=" * 60)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНОЕ ОБНОВЛЕНИЕ'}")
        print()
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из notion_sync_status
        cursor.execute("""
            SELECT event_id, page_id, page_url, sync_status, last_sync, created_at
            FROM notion_sync_status
            WHERE page_id IS NOT NULL
            ORDER BY created_at DESC
        """)
        
        db_records = cursor.fetchall()
        print(f"📊 Записей в SQLite с Page ID: {len(db_records)}")
        
        # Создаем словарь для быстрого поиска по page_id
        db_page_mapping = {}
        for record in db_records:
            event_id, page_id, page_url, sync_status, last_sync, created_at = record
            db_page_mapping[page_id] = {
                'event_id': event_id,
                'page_url': page_url,
                'sync_status': sync_status,
                'last_sync': last_sync,
                'created_at': created_at
            }
        
        # Получаем все страницы из Notion
        all_pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            payload = {
                "page_size": 100
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            all_pages.extend(data['results'])
            has_more = data['has_more']
            start_cursor = data.get('next_cursor')
        
        print(f"📊 Страниц в Notion: {len(all_pages)}")
        
        # Находим страницы без Event ID
        pages_to_update = []
        
        for page in all_pages:
            page_id = page['id']
            
            # Проверяем, есть ли Event ID
            has_event_id = False
            if 'properties' in page and 'Event ID' in page['properties']:
                event_id_prop = page['properties']['Event ID']
                if event_id_prop['type'] == 'rich_text' and event_id_prop['rich_text']:
                    has_event_id = True
            
            # Если нет Event ID, но есть запись в SQLite
            if not has_event_id and page_id in db_page_mapping:
                # Получаем название страницы
                title = ""
                if 'properties' in page and 'Name' in page['properties']:
                    title_prop = page['properties']['Name']
                    if title_prop['type'] == 'title' and title_prop['title']:
                        title = title_prop['title'][0]['text']['content']
                
                pages_to_update.append({
                    'page_id': page_id,
                    'title': title,
                    'event_id': db_page_mapping[page_id]['event_id'],
                    'created_time': page['created_time']
                })
        
        print(f"🔍 Найдено {len(pages_to_update)} страниц для обновления")
        print()
        
        if not pages_to_update:
            print("✅ Все страницы уже имеют Event ID!")
            return True
        
        # Показываем что будет обновлено
        print("📋 Страницы для обновления:")
        print("-" * 60)
        for i, page in enumerate(pages_to_update[:10], 1):  # Показываем первые 10
            print(f"{i:2d}. {page['title'][:40]:<40} | {page['event_id']}")
        
        if len(pages_to_update) > 10:
            print(f"    ... и еще {len(pages_to_update) - 10} страниц")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Ничего не обновлено")
            print("💡 Для реального обновления запустите: python tools/fill_notion_event_ids.py --execute")
            return True
        
        # Реальное обновление
        print("🔧 Начинаю обновление Event ID...")
        updated_count = 0
        errors = []
        
        for i, page in enumerate(pages_to_update, 1):
            try:
                page_id = page['page_id']
                event_id = page['event_id']
                title = page['title']
                
                # Обновляем Event ID
                url = f"https://api.notion.com/v1/pages/{page_id}"
                payload = {
                    "properties": {
                        "Event ID": {
                            "rich_text": [
                                {
                                    "text": {
                                        "content": event_id
                                    }
                                }
                            ]
                        }
                    }
                }
                
                response = requests.patch(url, headers=headers, json=payload)
                response.raise_for_status()
                
                updated_count += 1
                print(f"✅ {i:2d}/{len(pages_to_update)} Обновлена: {title[:40]} -> {event_id}")
                
            except Exception as e:
                error_msg = f"Ошибка обновления {page['title']}: {e}"
                errors.append(error_msg)
                print(f"❌ {i:2d}/{len(pages_to_update)} {error_msg}")
        
        print()
        print("📊 Результаты обновления:")
        print(f"✅ Успешно обновлено: {updated_count}")
        print(f"❌ Ошибок: {len(errors)}")
        
        if errors:
            print("\n❌ Ошибки:")
            for error in errors:
                print(f"  - {error}")
        
        conn.close()
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Ошибка при заполнении Event ID: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального обновления добавьте --execute")
        print()
    
    success = fill_notion_event_ids(dry_run=dry_run)
    
    if success:
        print("\n✅ Заполнение Event ID завершено успешно!")
    else:
        print("\n❌ Заполнение Event ID завершено с ошибками!")
        sys.exit(1)
