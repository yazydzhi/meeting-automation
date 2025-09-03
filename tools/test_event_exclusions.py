#!/usr/bin/env python3
"""
Скрипт для тестирования системы исключений событий.
"""

import os
import sys
from dotenv import load_dotenv

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.event_exclusions import EventExclusionManager, ExclusionType

def test_exclusions():
    """Тестирует систему исключений."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🧪 Тестирование системы исключений событий...")
    print("=" * 60)
    
    # Создаем менеджер исключений
    exclusion_manager = EventExclusionManager(config_manager=None)
    
    # Показываем статистику
    stats = exclusion_manager.get_exclusion_stats()
    print(f"📊 Статистика исключений:")
    print(f"  📄 Всего: {stats['total']}")
    print(f"  👤 Личные: {stats['personal']}")
    print(f"  🔧 Рабочие: {stats['work']}")
    print(f"  🔄 Общие: {stats['both']}")
    print(f"  🔤 Ключевые слова: {stats['keywords']}")
    print(f"  📝 Регулярные выражения: {stats['regex']}")
    print()
    
    # Тестовые события
    test_events = [
        # Личные события
        ("День рождения мамы", "personal"),
        ("Дела по дому", "personal"),
        ("Личная встреча", "personal"),
        ("Отпуск в горах", "personal"),
        ("Праздник семьи", "personal"),
        ("Выходной день", "personal"),
        ("Отдых на даче", "personal"),
        ("Напоминание о покупках", "personal"),
        ("Personal meeting", "personal"),
        
        # Рабочие события
        ("Обед с клиентом", "work"),
        ("Перерыв на кофе", "work"),
        ("Отгул по болезни", "work"),
        ("Больничный лист", "work"),
        ("Отпуск сотрудника", "work"),
        ("Праздничный день", "work"),
        ("Выходной в офисе", "work"),
        ("Напоминание о встрече", "work"),
        ("Reminder about deadline", "work"),
        ("Перекур с коллегами", "work"),
        ("Кофе-брейк", "work"),
        
        # События, которые НЕ должны исключаться
        ("Важная рабочая встреча", "work"),
        ("Презентация проекта", "work"),
        ("Планирование спринта", "work"),
        ("Личная тренировка", "personal"),
        ("Встреча с друзьями", "personal"),
        ("Важное личное дело", "personal"),
    ]
    
    print("🧪 Тестирование исключений:")
    print("-" * 60)
    
    excluded_count = 0
    included_count = 0
    
    for event_title, account_type in test_events:
        should_exclude = exclusion_manager.should_exclude_event(event_title, account_type)
        
        if should_exclude:
            print(f"🚫 ИСКЛЮЧЕНО: {event_title} ({account_type})")
            excluded_count += 1
        else:
            print(f"✅ ВКЛЮЧЕНО: {event_title} ({account_type})")
            included_count += 1
    
    print()
    print("📊 Результаты тестирования:")
    print(f"  🚫 Исключено событий: {excluded_count}")
    print(f"  ✅ Включено событий: {included_count}")
    print(f"  📄 Всего протестировано: {len(test_events)}")
    
    # Тестируем добавление новых исключений
    print(f"\n🔧 Тестирование добавления исключений:")
    print("-" * 60)
    
    # Добавляем регулярное выражение для тестирования
    test_regex = ".*[Тт]ест.*"
    success = exclusion_manager.add_exclusion("both", ExclusionType.REGEX, test_regex)
    
    if success:
        print(f"✅ Добавлено регулярное выражение: {test_regex}")
        
        # Тестируем новое исключение
        test_title = "Тестовая встреча"
        should_exclude = exclusion_manager.should_exclude_event(test_title, "work")
        
        if should_exclude:
            print(f"✅ Регулярное выражение работает: '{test_title}' исключено")
        else:
            print(f"❌ Регулярное выражение не работает: '{test_title}' не исключено")
        
        # Удаляем тестовое исключение
        exclusion_manager.remove_exclusion("both", ExclusionType.REGEX, test_regex)
        print(f"🗑️ Тестовое исключение удалено")
    
    # Показываем все исключения
    print(f"\n📋 Все настроенные исключения:")
    print("-" * 60)
    print(str(exclusion_manager))
    
    return True

if __name__ == "__main__":
    try:
        success = test_exclusions()
        
        if success:
            print("\n✅ Тестирование завершено успешно!")
        else:
            print("\n❌ Тестирование завершено с ошибками!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Ошибка тестирования: {e}")
        sys.exit(1)
