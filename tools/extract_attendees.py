#!/usr/bin/env python3
"""
Скрипт для извлечения участников из событий календаря.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.calendar_handler import CalendarHandler
import logging

def extract_attendees():
    """Извлекает участников из событий календаря."""
    
    try:
        print("👥 Извлечение участников из событий календаря...")
        print("=" * 60)
        
        # Инициализируем компоненты
        config_manager = ConfigManager()
        logger = logging.getLogger(__name__)
        calendar_handler = CalendarHandler(config_manager, logger)
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из processed_events
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, 
                   attendees, meeting_link, calendar_type, account_type
            FROM processed_events
            WHERE attendees IS NULL OR attendees = ''
            ORDER BY event_start_time DESC
        """)
        
        events_to_update = cursor.fetchall()
        print(f"📊 Событий без участников: {len(events_to_update)}")
        
        if not events_to_update:
            print("✅ Все события уже имеют участников!")
            return True
        
        # Загружаем текущие события календаря для извлечения участников
        calendar_events = {}
        
        for account_type in ['personal', 'work']:
            print(f"\n📅 Загрузка событий {account_type} календаря...")
            events = calendar_handler.get_calendar_events(account_type)
            
            for event in events:
                event_id = event.get('id')
                if event_id:
                    calendar_events[event_id] = event
        
        print(f"📊 Загружено событий из календаря: {len(calendar_events)}")
        
        # Извлекаем участников
        updated_count = 0
        
        for event_data in events_to_update:
            event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type = event_data
            
            # Ищем событие в календаре
            if event_id in calendar_events:
                calendar_event = calendar_events[event_id]
                
                # Извлекаем участников
                attendees_list = calendar_event.get('attendees', [])
                
                if attendees_list:
                    # Преобразуем список в строку
                    attendees_str = ', '.join(attendees_list)
                    
                    # Обновляем запись в базе данных
                    cursor.execute('''
                        UPDATE processed_events 
                        SET attendees = ?
                        WHERE event_id = ? AND account_type = ?
                    ''', (attendees_str, event_id, account_type))
                    
                    updated_count += 1
                    print(f"  ✅ {event_id}: {len(attendees_list)} участников")
                else:
                    print(f"  ❌ {event_id}: участники не найдены")
            else:
                print(f"  ⚠️ {event_id}: событие не найдено в календаре")
        
        conn.commit()
        
        print(f"\n📊 Результаты извлечения:")
        print(f"  ✅ Обновлено записей: {updated_count}")
        print(f"  ❌ Не найдено участников: {len(events_to_update) - updated_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при извлечении участников: {e}")
        return False

if __name__ == "__main__":
    success = extract_attendees()
    
    if success:
        print("\n✅ Извлечение участников завершено успешно!")
    else:
        print("\n❌ Извлечение завершено с ошибками!")
        sys.exit(1)
