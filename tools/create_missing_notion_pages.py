#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для создания недостающих страниц Notion для событий, у которых есть папки.
"""

import os
import sys
import sqlite3
from datetime import datetime
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager
from handlers.state_manager import StateManager
from handlers.notion_handler import NotionHandler


def create_missing_notion_pages():
    """Создает недостающие страницы Notion для событий с папками."""
    print("📝 Создание недостающих страниц Notion...")
    
    try:
        config_manager = ConfigManager()
        state_manager = StateManager()
        notion_handler = NotionHandler(config_manager, None, None)
        
        # Получаем события, у которых есть папки, но нет страниц в Notion
        with sqlite3.connect(state_manager.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT
                    pe.event_id,
                    pe.event_title,
                    pe.event_start_time,
                    pe.event_end_time,
                    pe.account_type,
                    fcs.folder_path
                FROM processed_events pe
                JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id AND pe.account_type = fcs.account_type
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                WHERE fcs.status = 'success' 
                AND nss.event_id IS NULL
                ORDER BY pe.processed_at DESC
            ''')
            
            events_without_notion = cursor.fetchall()
        
        if not events_without_notion:
            print("✅ Все события уже имеют страницы в Notion")
            return
        
        print(f"📋 Найдено {len(events_without_notion)} событий без страниц в Notion")
        
        created_count = 0
        error_count = 0
        
        for event_data in events_without_notion:
            event_id, event_title, start_time, end_time, account_type, folder_path = event_data
            
            print(f"\n📝 Создаю страницу Notion для: {event_title}")
            
            try:
                # Создаем объект события
                event = {
                    'id': event_id,
                    'title': event_title,
                    'start': start_time,
                    'end': end_time,
                    'attendees': []
                }
                
                # Создаем страницу в Notion
                notion_result = notion_handler.create_meeting_page(event, folder_path, account_type)
                
                if notion_result.get('success'):
                    page_id = notion_result.get('page_id')
                    print(f"  ✅ Страница создана: {page_id}")
                    
                    # Помечаем в БД
                    state_manager.mark_notion_synced(
                        event_id, 
                        page_id, 
                        notion_result.get('page_url', ''), 
                        "success"
                    )
                    created_count += 1
                else:
                    print(f"  ❌ Ошибка создания: {notion_result.get('message', 'Unknown error')}")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ❌ Критическая ошибка: {e}")
                error_count += 1
        
        print(f"\n📊 Результат:")
        print(f"  ✅ Создано страниц: {created_count}")
        print(f"  ❌ Ошибок: {error_count}")
        
    except Exception as e:
        print(f"❌ Ошибка создания страниц Notion: {e}")


def main():
    """Основная функция."""
    print("🚀 Запуск создания недостающих страниц Notion...")
    print("=" * 60)
    
    create_missing_notion_pages()
    
    print("=" * 60)
    print("✅ Создание страниц Notion завершено!")


if __name__ == "__main__":
    main()
