#!/usr/bin/env python3
"""
Скрипт для обновления деталей событий в базе данных.
Заполняет недостающие данные: attendees, meeting_link, calendar_type.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def update_event_details():
    """Обновляет детали событий в базе данных."""
    
    try:
        print("🔧 Обновление деталей событий в базе данных...")
        print("=" * 60)
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из processed_events
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, 
                   attendees, meeting_link, calendar_type, account_type
            FROM processed_events
            ORDER BY event_start_time DESC
        """)
        
        events = cursor.fetchall()
        print(f"📊 Событий в базе данных: {len(events)}")
        
        # Анализируем, какие данные отсутствуют
        missing_attendees = 0
        missing_meeting_link = 0
        missing_calendar_type = 0
        
        for event in events:
            event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type = event
            
            if not attendees:
                missing_attendees += 1
            if not meeting_link:
                missing_meeting_link += 1
            if not calendar_type:
                missing_calendar_type += 1
        
        print(f"\n📋 Анализ недостающих данных:")
        print(f"  ❌ Отсутствуют участники: {missing_attendees}")
        print(f"  ❌ Отсутствуют ссылки на встречи: {missing_meeting_link}")
        print(f"  ❌ Отсутствует тип календаря: {missing_calendar_type}")
        
        if missing_attendees == 0 and missing_meeting_link == 0 and missing_calendar_type == 0:
            print("\n✅ Все данные уже заполнены!")
            return True
        
        # Определяем тип календаря на основе event_id
        print(f"\n🔧 Обновление данных...")
        
        updated_count = 0
        
        for event in events:
            event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type = event
            
            # Определяем тип календаря на основе event_id
            new_calendar_type = calendar_type
            if not new_calendar_type:
                if event_id.startswith('ical_'):
                    new_calendar_type = 'ical_calendar'
                elif event_id.startswith('google_') or '@' in event_id:
                    new_calendar_type = 'google_calendar'
                else:
                    new_calendar_type = 'unknown'
            
            # Если есть изменения, обновляем запись
            if (not attendees or not meeting_link or not calendar_type) and new_calendar_type:
                cursor.execute('''
                    UPDATE processed_events 
                    SET calendar_type = ?
                    WHERE event_id = ? AND account_type = ?
                ''', (new_calendar_type, event_id, account_type))
                
                updated_count += 1
                print(f"  ✅ Обновлен {event_id}: calendar_type = {new_calendar_type}")
        
        conn.commit()
        
        print(f"\n📊 Результаты обновления:")
        print(f"  ✅ Обновлено записей: {updated_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при обновлении деталей событий: {e}")
        return False

if __name__ == "__main__":
    success = update_event_details()
    
    if success:
        print("\n✅ Обновление деталей событий завершено успешно!")
    else:
        print("\n❌ Обновление завершено с ошибками!")
        sys.exit(1)
