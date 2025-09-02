#!/usr/bin/env python3
"""
Скрипт для проверки дубликатов в записях Notion.
"""

import sqlite3
import sys
from collections import defaultdict

def check_notion_duplicates():
    """Проверяет дубликаты в таблице notion_sync_status."""
    
    # Подключаемся к базе данных
    db_path = "data/system_state.db"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Проверка дубликатов в записях Notion...")
        print("=" * 60)
        
        # Получаем все записи
        cursor.execute("""
            SELECT id, event_id, page_id, page_url, sync_status, last_sync, created_at
            FROM notion_sync_status
            ORDER BY created_at DESC
        """)
        
        records = cursor.fetchall()
        print(f"📊 Всего записей в notion_sync_status: {len(records)}")
        
        # Проверяем дубликаты по event_id
        event_id_counts = defaultdict(list)
        page_id_counts = defaultdict(list)
        
        for record in records:
            record_id, event_id, page_id, page_url, sync_status, last_sync, created_at = record
            event_id_counts[event_id].append(record)
            if page_id:  # Только если page_id не None
                page_id_counts[page_id].append(record)
        
        # Анализируем дубликаты по event_id
        print("\n🔍 Анализ дубликатов по Event ID:")
        print("-" * 40)
        event_duplicates = {k: v for k, v in event_id_counts.items() if len(v) > 1}
        
        if event_duplicates:
            print(f"❌ Найдено {len(event_duplicates)} Event ID с дубликатами:")
            for event_id, records in event_duplicates.items():
                print(f"\n  Event ID: {event_id}")
                for record in records:
                    record_id, _, page_id, page_url, sync_status, last_sync, created_at = record
                    print(f"    ID: {record_id}, Page ID: {page_id[:20] if page_id else 'None'}..., Status: {sync_status}, Created: {created_at}")
        else:
            print("✅ Дубликатов по Event ID не найдено")
        
        # Анализируем дубликаты по page_id
        print("\n🔍 Анализ дубликатов по Page ID:")
        print("-" * 40)
        page_duplicates = {k: v for k, v in page_id_counts.items() if len(v) > 1}
        
        if page_duplicates:
            print(f"❌ Найдено {len(page_duplicates)} Page ID с дубликатами:")
            for page_id, records in page_duplicates.items():
                print(f"\n  Page ID: {page_id}")
                for record in records:
                    record_id, event_id, _, page_url, sync_status, last_sync, created_at = record
                    print(f"    ID: {record_id}, Event ID: {event_id}, Status: {sync_status}, Created: {created_at}")
        else:
            print("✅ Дубликатов по Page ID не найдено")
        
        # Проверяем записи с одинаковыми event_id но разными page_id
        print("\n🔍 Анализ записей с одинаковым Event ID но разными Page ID:")
        print("-" * 50)
        event_page_mismatches = []
        
        for event_id, event_records in event_id_counts.items():
            if len(event_records) > 1:
                page_ids = [record[2] for record in event_records]
                if len(set(page_ids)) > 1:
                    event_page_mismatches.append((event_id, event_records))
        
        if event_page_mismatches:
            print(f"❌ Найдено {len(event_page_mismatches)} Event ID с разными Page ID:")
            for event_id, event_records in event_page_mismatches:
                print(f"\n  Event ID: {event_id}")
                for record in event_records:
                    record_id, _, page_id, page_url, sync_status, last_sync, created_at = record
                    print(f"    ID: {record_id}, Page ID: {page_id}, Status: {sync_status}, Created: {created_at}")
        else:
            print("✅ Все записи с одинаковым Event ID имеют одинаковый Page ID")
        
        # Проверяем записи с пустыми page_id
        print("\n🔍 Анализ записей с пустыми Page ID:")
        print("-" * 40)
        empty_page_records = [record for record in records if not record[2]]  # page_id is None or empty
        if empty_page_records:
            print(f"❌ Найдено {len(empty_page_records)} записей с пустыми Page ID:")
            for record in empty_page_records:
                record_id, event_id, page_id, page_url, sync_status, last_sync, created_at = record
                print(f"    ID: {record_id}, Event ID: {event_id}, Status: {sync_status}, Created: {created_at}")
        else:
            print("✅ Все записи имеют Page ID")
        
        # Статистика
        print("\n📊 Статистика:")
        print("-" * 20)
        print(f"Всего записей: {len(records)}")
        print(f"Уникальных Event ID: {len(event_id_counts)}")
        print(f"Уникальных Page ID: {len(page_id_counts)}")
        print(f"Записей с пустыми Page ID: {len(empty_page_records)}")
        print(f"Дубликатов по Event ID: {len(event_duplicates)}")
        print(f"Дубликатов по Page ID: {len(page_duplicates)}")
        print(f"Event ID с разными Page ID: {len(event_page_mismatches)}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при проверке дубликатов: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_notion_duplicates()
