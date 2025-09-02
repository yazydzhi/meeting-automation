#!/usr/bin/env python3
"""
Скрипт для проверки исходных данных календаря.
Проверяет, какие данные доступны в исходных событиях календаря.
"""

import os
import sys

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.calendar_handler import CalendarHandler
import logging

def check_calendar_source_data():
    """Проверяет исходные данные календаря."""
    
    try:
        print("🔍 Проверка исходных данных календаря...")
        print("=" * 60)
        
        # Инициализируем компоненты
        config_manager = ConfigManager()
        logger = logging.getLogger(__name__)
        calendar_handler = CalendarHandler(config_manager, logger)
        
        # Проверяем оба типа аккаунтов
        for account_type in ['personal', 'work']:
            print(f"\n📅 Проверка {account_type} аккаунта:")
            print("-" * 40)
            
            # Загружаем события календаря
            events = calendar_handler.get_calendar_events(account_type)
            
            if not events:
                print(f"  ❌ События не найдены для {account_type}")
                continue
            
            print(f"  📊 Найдено событий: {len(events)}")
            
            # Анализируем первые 5 событий
            for i, event in enumerate(events[:5], 1):
                print(f"\n  📋 Событие {i}:")
                print(f"    ID: {event.get('id', 'N/A')}")
                print(f"    Название: {event.get('title', 'N/A')}")
                print(f"    Начало: {event.get('start', 'N/A')}")
                print(f"    Конец: {event.get('end', 'N/A')}")
                print(f"    Участники: {event.get('attendees', 'N/A')}")
                print(f"    Описание: {event.get('description', 'N/A')[:50]}...")
                print(f"    Местоположение: {event.get('location', 'N/A')}")
                print(f"    HTML ссылка: {event.get('html_link', 'N/A')}")
                print(f"    Источник: {event.get('source', 'N/A')}")
            
            # Статистика по полям
            print(f"\n  📊 Статистика по полям:")
            total_events = len(events)
            
            fields_stats = {
                'attendees': sum(1 for e in events if e.get('attendees')),
                'description': sum(1 for e in events if e.get('description')),
                'location': sum(1 for e in events if e.get('location')),
                'html_link': sum(1 for e in events if e.get('html_link')),
                'source': sum(1 for e in events if e.get('source'))
            }
            
            for field, count in fields_stats.items():
                percentage = (count / total_events) * 100 if total_events > 0 else 0
                print(f"    {field}: {count}/{total_events} ({percentage:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке исходных данных календаря: {e}")
        return False

if __name__ == "__main__":
    success = check_calendar_source_data()
    
    if success:
        print("\n✅ Проверка исходных данных завершена успешно!")
    else:
        print("\n❌ Проверка завершена с ошибками!")
        sys.exit(1)
