#!/usr/bin/env python3
"""
Скрипт для синхронизации данных между SQLite и Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def sync_notion_sqlite(dry_run=True):
    """Синхронизирует данные между SQLite и Notion."""
    
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
        
        print("🔄 Синхронизация данных между SQLite и Notion...")
        print("=" * 60)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНАЯ СИНХРОНИЗАЦИЯ'}")
        print()
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из notion_sync_status
        cursor.execute("""
            SELECT id, event_id, page_id, page_url, sync_status, last_sync, created_at
            FROM notion_sync_status
            ORDER BY created_at DESC
        """)
        
        db_records = cursor.fetchall()
        print(f"📊 Записей в SQLite: {len(db_records)}")
        
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
        
        # Создаем словари для анализа
        db_page_ids = set()
        notion_page_ids = set()
        db_event_ids = set()
        notion_event_ids = set()
        
        # Анализируем SQLite данные
        for record in db_records:
            record_id, event_id, page_id, page_url, sync_status, last_sync, created_at = record
            if page_id:
                db_page_ids.add(page_id)
            if event_id:
                db_event_ids.add(event_id)
        
        # Анализируем Notion данные
        for page in all_pages:
            page_id = page['id']
            notion_page_ids.add(page_id)
            
            # Получаем Event ID
            if 'properties' in page and 'Event ID' in page['properties']:
                event_id_prop = page['properties']['Event ID']
                if event_id_prop['type'] == 'rich_text' and event_id_prop['rich_text']:
                    event_id = event_id_prop['rich_text'][0]['text']['content']
                    if event_id:
                        notion_event_ids.add(event_id)
        
        # Анализ несоответствий
        print("\n🔍 Анализ несоответствий:")
        print("-" * 40)
        
        # Страницы в SQLite, но не в Notion
        sqlite_only = db_page_ids - notion_page_ids
        print(f"📊 Страницы только в SQLite: {len(sqlite_only)}")
        
        # Страницы в Notion, но не в SQLite
        notion_only = notion_page_ids - db_page_ids
        print(f"📊 Страницы только в Notion: {len(notion_only)}")
        
        # Event ID в SQLite, но не в Notion
        sqlite_event_only = db_event_ids - notion_event_ids
        print(f"📊 Event ID только в SQLite: {len(sqlite_event_only)}")
        
        # Event ID в Notion, но не в SQLite
        notion_event_only = notion_event_ids - db_event_ids
        print(f"📊 Event ID только в Notion: {len(notion_event_only)}")
        
        # Общие страницы
        common_pages = db_page_ids & notion_page_ids
        print(f"📊 Общие страницы: {len(common_pages)}")
        
        print()
        
        # Показываем детали несоответствий
        if sqlite_only:
            print("🔍 Страницы только в SQLite:")
            for page_id in list(sqlite_only)[:5]:
                print(f"  - {page_id}")
            if len(sqlite_only) > 5:
                print(f"  ... и еще {len(sqlite_only) - 5}")
            print()
        
        if notion_only:
            print("🔍 Страницы только в Notion:")
            for page_id in list(notion_only)[:5]:
                print(f"  - {page_id}")
            if len(notion_only) > 5:
                print(f"  ... и еще {len(notion_only) - 5}")
            print()
        
        if sqlite_event_only:
            print("🔍 Event ID только в SQLite:")
            for event_id in list(sqlite_event_only)[:5]:
                print(f"  - {event_id}")
            if len(sqlite_event_only) > 5:
                print(f"  ... и еще {len(sqlite_event_only) - 5}")
            print()
        
        if notion_event_only:
            print("🔍 Event ID только в Notion:")
            for event_id in list(notion_event_only)[:5]:
                print(f"  - {event_id}")
            if len(notion_event_only) > 5:
                print(f"  ... и еще {len(notion_event_only) - 5}")
            print()
        
        # Рекомендации
        print("💡 Рекомендации:")
        print("-" * 20)
        
        if len(notion_only) > len(db_page_ids):
            print("⚠️ В Notion значительно больше страниц, чем в SQLite")
            print("   Рекомендуется сначала очистить дубликаты в Notion")
        
        if len(sqlite_event_only) > 0:
            print("⚠️ Есть Event ID в SQLite, которых нет в Notion")
            print("   Рекомендуется заполнить Event ID в Notion")
        
        if len(notion_event_only) > 0:
            print("⚠️ Есть Event ID в Notion, которых нет в SQLite")
            print("   Возможно, нужно обновить SQLite базу")
        
        if len(sqlite_only) > 0:
            print("⚠️ Есть страницы в SQLite, которых нет в Notion")
            print("   Возможно, нужно создать недостающие страницы в Notion")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Только анализ, никаких изменений")
            print("💡 Для реальной синхронизации запустите: python tools/sync_notion_sqlite.py --execute")
            return True
        
        # Здесь можно добавить логику реальной синхронизации
        print("🔧 Реальная синхронизация пока не реализована")
        print("💡 Используйте отдельные скрипты для очистки и заполнения данных")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при синхронизации: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реальной синхронизации добавьте --execute")
        print()
    
    success = sync_notion_sqlite(dry_run=dry_run)
    
    if success:
        print("\n✅ Синхронизация завершена успешно!")
    else:
        print("\n❌ Синхронизация завершена с ошибками!")
        sys.exit(1)
