#!/usr/bin/env python3
"""
Скрипт для создания всех недостающих страниц Notion для событий с папками.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.state_manager import StateManager
from src.handlers.notion_handler import NotionHandler

def find_events_without_notion_pages():
    """
    Находит события с папками, но без страниц Notion.
    """
    print("🔍 Поиск событий без страниц Notion...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT pe.event_id, pe.event_title, pe.account_type, pe.event_start_time, pe.event_end_time, fcs.folder_path
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id
        WHERE fcs.status = 'success' 
        AND pe.event_id NOT IN (
            SELECT event_id FROM notion_sync_status WHERE sync_status = 'success'
        )
        ORDER BY pe.processed_at DESC
    ''')
    
    events = cursor.fetchall()
    conn.close()
    
    print(f"📊 Найдено {len(events)} событий без страниц Notion")
    return events

def create_notion_page_for_event(event_data):
    """
    Создает страницу Notion для события.
    """
    event_id, event_title, account_type, start_time, end_time, folder_path = event_data
    
    print(f"\n🔧 Создание страницы Notion для: {event_title}")
    print(f"  🆔 Event ID: {event_id}")
    print(f"  👤 Account: {account_type}")
    print(f"  📂 Папка: {folder_path}")
    
    try:
        # Инициализируем компоненты
        config_manager = ConfigManager()
        state_manager = StateManager()
        notion_handler = NotionHandler(config_manager)
        
        # Подготавливаем данные события для Notion
        event_data_dict = {
            'id': event_id,
            'title': event_title,
            'account_type': account_type,
            'start_time': start_time if start_time else '',
            'end_time': end_time if end_time else '',
            'folder_path': folder_path
        }
        
        # Создаем страницу в Notion
        notion_result = notion_handler.create_meeting_page(event_data_dict, folder_path, account_type)
        
        if notion_result and notion_result.get('success'):
            page_id = notion_result.get('page_id', 'unknown')
            page_url = notion_result.get('page_url', '')
            
            print(f"  ✅ Страница создана: {page_id}")
            
            # Обновляем базу данных
            state_manager.mark_notion_synced(event_id, page_id, page_url, "success")
            
            return True
        else:
            print(f"  ❌ Ошибка создания: {notion_result}")
            return False
            
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")
        return False

def create_all_missing_pages():
    """
    Создает все недостающие страницы Notion.
    """
    events = find_events_without_notion_pages()
    
    if not events:
        print("✅ Все события уже имеют страницы Notion")
        return
    
    print(f"\n🔧 Создание {len(events)} недостающих страниц Notion...")
    
    success_count = 0
    error_count = 0
    
    for event_data in events:
        try:
            if create_notion_page_for_event(event_data):
                success_count += 1
            else:
                error_count += 1
        except Exception as e:
            print(f"  ❌ Критическая ошибка: {e}")
            error_count += 1
    
    print(f"\n📊 Результат создания страниц:")
    print(f"  ✅ Успешно создано: {success_count}")
    print(f"  ❌ Ошибок: {error_count}")
    print(f"  📈 Процент успеха: {(success_count/(success_count+error_count)*100):.1f}%")

def verify_results():
    """
    Проверяет результаты создания страниц.
    """
    print(f"\n🔍 Проверка результатов...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Подсчитываем события с папками
    cursor.execute('''
        SELECT COUNT(DISTINCT pe.event_id) 
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id
        WHERE fcs.status = 'success'
    ''')
    events_with_folders = cursor.fetchone()[0]
    
    # Подсчитываем события с страницами Notion
    cursor.execute('''
        SELECT COUNT(DISTINCT pe.event_id) 
        FROM processed_events pe
        INNER JOIN notion_sync_status nss ON pe.event_id = nss.event_id
        WHERE nss.sync_status = 'success'
    ''')
    events_with_notion = cursor.fetchone()[0]
    
    # Подсчитываем общее количество страниц Notion
    cursor.execute('SELECT COUNT(*) FROM notion_sync_status WHERE sync_status = "success"')
    total_notion_pages = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Статистика после создания страниц:")
    print(f"  📁 Событий с папками: {events_with_folders}")
    print(f"  📝 Событий с страницами Notion: {events_with_notion}")
    print(f"  📄 Всего страниц Notion: {total_notion_pages}")
    print(f"  📈 Покрытие Notion: {(events_with_notion/events_with_folders*100):.1f}%")

if __name__ == "__main__":
    try:
        create_all_missing_pages()
        verify_results()
        print(f"\n✅ Создание недостающих страниц Notion завершено!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
