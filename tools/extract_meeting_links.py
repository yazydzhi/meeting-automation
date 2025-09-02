#!/usr/bin/env python3
"""
Скрипт для извлечения ссылок на встречи из описаний событий календаря.
"""

import os
import sys
import sqlite3
import re
from datetime import datetime

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.calendar_handler import CalendarHandler
import logging

def extract_meeting_links():
    """Извлекает ссылки на встречи из описаний событий календаря."""
    
    try:
        print("🔗 Извлечение ссылок на встречи из описаний событий...")
        print("=" * 70)
        
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
            WHERE meeting_link IS NULL OR meeting_link = ''
            ORDER BY event_start_time DESC
        """)
        
        events_to_update = cursor.fetchall()
        print(f"📊 Событий без ссылок на встречи: {len(events_to_update)}")
        
        if not events_to_update:
            print("✅ Все события уже имеют ссылки на встречи!")
            return True
        
        # Загружаем текущие события календаря для извлечения описаний
        calendar_events = {}
        
        for account_type in ['personal', 'work']:
            print(f"\n📅 Загрузка событий {account_type} календаря...")
            events = calendar_handler.get_calendar_events(account_type)
            
            for event in events:
                event_id = event.get('id')
                if event_id:
                    calendar_events[event_id] = event
        
        print(f"📊 Загружено событий из календаря: {len(calendar_events)}")
        
        # Извлекаем ссылки на встречи
        updated_count = 0
        
        for event_data in events_to_update:
            event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type = event_data
            
            # Ищем событие в календаре
            if event_id in calendar_events:
                calendar_event = calendar_events[event_id]
                
                # Извлекаем ссылку на встречу из описания
                description = calendar_event.get('description', '')
                location = calendar_event.get('location', '')
                
                meeting_link = extract_meeting_link_from_text(description, location)
                
                if meeting_link:
                    # Обновляем запись в базе данных
                    cursor.execute('''
                        UPDATE processed_events 
                        SET meeting_link = ?
                        WHERE event_id = ? AND account_type = ?
                    ''', (meeting_link, event_id, account_type))
                    
                    updated_count += 1
                    print(f"  ✅ {event_id}: {meeting_link}")
                else:
                    print(f"  ❌ {event_id}: ссылка не найдена")
            else:
                print(f"  ⚠️ {event_id}: событие не найдено в календаре")
        
        conn.commit()
        
        print(f"\n📊 Результаты извлечения:")
        print(f"  ✅ Обновлено записей: {updated_count}")
        print(f"  ❌ Не найдено ссылок: {len(events_to_update) - updated_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при извлечении ссылок на встречи: {e}")
        return False

def extract_meeting_link_from_text(description: str, location: str = "") -> str:
    """
    Извлекает ссылку на встречу из текста описания или местоположения.
    
    Args:
        description: Описание события
        location: Местоположение события
        
    Returns:
        Ссылка на встречу или пустая строка
    """
    if not description and not location:
        return ""
    
    # Объединяем описание и местоположение
    text = f"{description} {location}".strip()
    
    # Паттерны для поиска ссылок на встречи
    patterns = [
        # Google Meet
        r'https://meet\.google\.com/[a-zA-Z0-9\-]+',
        r'meet\.google\.com/[a-zA-Z0-9\-]+',
        
        # Zoom
        r'https://[a-zA-Z0-9\-]+\.zoom\.us/j/[0-9]+',
        r'zoom\.us/j/[0-9]+',
        
        # Microsoft Teams
        r'https://teams\.microsoft\.com/l/meetup-join/[a-zA-Z0-9\-%]+',
        r'teams\.microsoft\.com/l/meetup-join/[a-zA-Z0-9\-%]+',
        
        # Общие паттерны для ссылок
        r'https://[a-zA-Z0-9\-\.]+/[a-zA-Z0-9\-/]+',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Возвращаем первую найденную ссылку
            link = matches[0]
            
            # Если ссылка не начинается с https://, добавляем
            if not link.startswith('http'):
                link = f"https://{link}"
            
            return link
    
    return ""

if __name__ == "__main__":
    success = extract_meeting_links()
    
    if success:
        print("\n✅ Извлечение ссылок на встречи завершено успешно!")
    else:
        print("\n❌ Извлечение завершено с ошибками!")
        sys.exit(1)
