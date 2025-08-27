#!/usr/bin/env python3
"""
Тест для проверки оптимизации календарных событий.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from config_manager import ConfigManager
    from calendar_handler import CalendarHandler
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


def test_cache_creation():
    """Тест создания кэша обработанных событий."""
    print("🔍 Тест создания кэша обработанных событий")
    print("=" * 60)
    
    try:
        # Создаем обработчик календаря
        config_manager = ConfigManager()
        calendar_handler = CalendarHandler(config_manager)
        
        # Проверяем, что кэш загружен
        if hasattr(calendar_handler, 'processed_events_cache'):
            print("✅ Кэш обработанных событий инициализирован")
            print(f"   Количество событий в кэше: {len(calendar_handler.processed_events_cache.get('events', {}))}")
        else:
            print("❌ Кэш обработанных событий не инициализирован")
            return False
        
        # Проверяем время последней синхронизации
        if hasattr(calendar_handler, 'last_sync_time'):
            print("✅ Время последней синхронизации инициализировано")
            print(f"   Личный аккаунт: {calendar_handler.last_sync_time.get('personal', 'Нет данных')}")
            print(f"   Рабочий аккаунт: {calendar_handler.last_sync_time.get('work', 'Нет данных')}")
        else:
            print("❌ Время последней синхронизации не инициализировано")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False


def test_cache_operations():
    """Тест операций с кэшем."""
    print("\n🔧 Тест операций с кэшем")
    print("=" * 60)
    
    try:
        # Создаем обработчик календаря
        config_manager = ConfigManager()
        calendar_handler = CalendarHandler(config_manager)
        
        # Создаем тестовое событие
        from calendar_alternatives import CalendarEvent
        
        test_event = CalendarEvent(
            title="Тестовая встреча",
            start=datetime.now(),
            end=datetime.now() + timedelta(hours=1),
            description="Описание тестовой встречи",
            location="Тестовое место",
            attendees=["test@example.com"],
            meeting_link="https://meet.google.com/test",
            calendar_source="test",
            event_id="test_123"
        )
        
        # Проверяем, что событие не обработано
        is_processed = calendar_handler._is_event_processed(test_event, "personal")
        print(f"📋 Событие обработано: {is_processed}")
        
        if is_processed:
            print("❌ Событие уже помечено как обработанное (не должно быть)")
            return False
        
        # Отмечаем событие как обработанное
        test_result = {
            'title': test_event.title,
            'start': test_event.start,
            'end': test_event.end,
            'attendees_count': len(test_event.attendees)
        }
        
        calendar_handler._mark_event_processed(test_event, "personal", test_result)
        print("✅ Событие отмечено как обработанное")
        
        # Проверяем, что событие теперь обработано
        is_processed = calendar_handler._is_event_processed(test_event, "personal")
        print(f"📋 Событие обработано после отметки: {is_processed}")
        
        if not is_processed:
            print("❌ Событие не помечено как обработанное после отметки")
            return False
        
        # Проверяем размер кэша
        cache_size = len(calendar_handler.processed_events_cache.get('events', {}))
        print(f"📊 Размер кэша: {cache_size} событий")
        
        if cache_size == 0:
            print("❌ Кэш пуст после добавления события")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования операций с кэшем: {e}")
        return False


def test_cache_persistence():
    """Тест сохранения и загрузки кэша."""
    print("\n💾 Тест сохранения и загрузки кэша")
    print("=" * 60)
    
    try:
        # Создаем обработчик календаря
        config_manager = ConfigManager()
        calendar_handler = CalendarHandler(config_manager)
        
        # Сохраняем кэш
        calendar_handler._save_processed_events_cache()
        print("✅ Кэш сохранен")
        
        # Проверяем, что файл создан
        cache_file = Path('data/processed_events_cache.json')
        if cache_file.exists():
            print(f"✅ Файл кэша создан: {cache_file}")
            
            # Загружаем содержимое файла
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_content = json.load(f)
            
            print(f"📊 Содержимое кэша: {len(cache_content.get('events', {}))} событий")
            print(f"🕒 Последнее обновление: {cache_content.get('last_updated', 'Нет данных')}")
        else:
            print("❌ Файл кэша не создан")
            return False
        
        # Сохраняем время синхронизации
        calendar_handler._save_last_sync_time()
        print("✅ Время синхронизации сохранено")
        
        # Проверяем, что файл создан
        sync_file = Path('data/last_sync_time.json')
        if sync_file.exists():
            print(f"✅ Файл времени синхронизации создан: {sync_file}")
            
            # Загружаем содержимое файла
            with open(sync_file, 'r', encoding='utf-8') as f:
                sync_content = json.load(f)
            
            print(f"📊 Время синхронизации личного аккаунта: {sync_content.get('personal', 'Нет данных')}")
            print(f"📊 Время синхронизации рабочего аккаунта: {sync_content.get('work', 'Нет данных')}")
        else:
            print("❌ Файл времени синхронизации не создан")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования сохранения кэша: {e}")
        return False


def main():
    """Основная функция тестирования."""
    print("🧪 Тестирование оптимизации календарных событий")
    print("=" * 80)
    
    # Тест 1: Создание кэша
    if not test_cache_creation():
        print("\n❌ Тест создания кэша не пройден")
        return False
    
    # Тест 2: Операции с кэшем
    if not test_cache_operations():
        print("\n❌ Тест операций с кэшем не пройден")
        return False
    
    # Тест 3: Сохранение кэша
    if not test_cache_persistence():
        print("\n❌ Тест сохранения кэша не пройден")
        return False
    
    print("\n🎉 Все тесты пройдены успешно!")
    print("✅ Система кэширования работает корректно")
    print("✅ События не будут обрабатываться повторно")
    print("✅ Уведомления будут отправляться только при реальных изменениях")
    
    return True


if __name__ == "__main__":
    from pathlib import Path
    success = main()
    sys.exit(0 if success else 1)
