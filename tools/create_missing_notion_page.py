#!/usr/bin/env python3
"""
Скрипт для создания недостающей страницы Notion для конкретного события.
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

def create_notion_page_for_event(event_id, event_title, account_type):
    """
    Создает страницу Notion для конкретного события.
    """
    print(f"🔧 Создание страницы Notion для события: {event_title}")
    print(f"  🆔 Event ID: {event_id}")
    print(f"  👤 Account: {account_type}")
    
    try:
        # Инициализируем компоненты
        config_manager = ConfigManager()
        state_manager = StateManager()
        notion_handler = NotionHandler(config_manager)
        
        # Получаем информацию о событии из базы данных
        conn = sqlite3.connect('data/system_state.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT event_id, event_title, account_type, event_start_time, event_end_time
            FROM processed_events 
            WHERE event_id = ?
        ''', (event_id,))
        
        event_data = cursor.fetchone()
        if not event_data:
            print(f"❌ Событие не найдено в базе данных: {event_id}")
            return False
        
        # Получаем путь к папке
        cursor.execute('''
            SELECT folder_path FROM folder_creation_status 
            WHERE event_id = ? AND account_type = ? AND status = 'success'
        ''', (event_id, account_type))
        
        folder_result = cursor.fetchone()
        if not folder_result:
            print(f"❌ Папка не найдена для события: {event_id}")
            return False
        
        folder_path = folder_result[0]
        conn.close()
        
        # Подготавливаем данные события для Notion
        event_data_dict = {
            'id': event_id,
            'title': event_title,
            'account_type': account_type,
            'start_time': event_data[3] if event_data[3] else '',
            'end_time': event_data[4] if event_data[4] else '',
            'folder_path': folder_path
        }
        
        print(f"  📂 Папка: {folder_path}")
        print(f"  📅 Время начала: {event_data_dict['start_time']}")
        print(f"  📅 Время окончания: {event_data_dict['end_time']}")
        
        # Создаем страницу в Notion
        print(f"  📝 Создание страницы в Notion...")
        notion_result = notion_handler.create_meeting_page(event_data_dict, folder_path, account_type)
        
        if notion_result and notion_result.get('success'):
            page_id = notion_result.get('page_id', 'unknown')
            page_url = notion_result.get('page_url', '')
            
            print(f"  ✅ Страница создана успешно!")
            print(f"  🆔 Page ID: {page_id}")
            print(f"  🔗 URL: {page_url}")
            
            # Обновляем базу данных
            state_manager.mark_notion_synced(event_id, page_id, page_url, "success")
            print(f"  💾 Запись добавлена в базу данных")
            
            return True
        else:
            print(f"  ❌ Ошибка создания страницы: {notion_result}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при создании страницы Notion: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_notion_page_creation(event_id):
    """
    Проверяет, что страница Notion была создана.
    """
    print(f"\n🔍 Проверка создания страницы Notion...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT page_id, page_url, sync_status, last_sync 
        FROM notion_sync_status 
        WHERE event_id = ?
    ''', (event_id,))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        page_id, page_url, sync_status, last_sync = result
        print(f"  ✅ Страница найдена в базе данных:")
        print(f"    🆔 Page ID: {page_id}")
        print(f"    🔗 URL: {page_url}")
        print(f"    📊 Статус: {sync_status}")
        print(f"    ⏰ Время: {last_sync}")
        return True
    else:
        print(f"  ❌ Страница не найдена в базе данных")
        return False

if __name__ == "__main__":
    # Параметры для события "ПСБ //SmartDeal - эквайринг"
    event_id = "ical_2025-08-29_84286d0f"
    event_title = "ПСБ //SmartDeal - эквайринг"
    account_type = "work"
    
    try:
        success = create_notion_page_for_event(event_id, event_title, account_type)
        
        if success:
            verify_notion_page_creation(event_id)
            print(f"\n✅ Создание страницы Notion завершено успешно!")
        else:
            print(f"\n❌ Не удалось создать страницу Notion")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
