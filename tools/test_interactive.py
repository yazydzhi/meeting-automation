#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для демонстрации улучшенного интерактивного режима.
"""

import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

from tools.db_viewer import DatabaseViewer

def demo_interactive_features():
    """Демонстрация новых возможностей."""
    print("🔍 ДЕМОНСТРАЦИЯ УЛУЧШЕННОГО DB VIEWER")
    print("=" * 60)
    
    # Создаем viewer
    viewer = DatabaseViewer('data/system_state.db')
    
    if not viewer.connect():
        print("❌ Не удалось подключиться к базе данных")
        return
    
    try:
        print("\n📊 1. Общая статистика:")
        print("-" * 30)
        viewer.show_statistics()
        
        print("\n📅 2. События с датой и временем:")
        print("-" * 30)
        viewer.show_processed_events(3)
        
        print("\n📊 3. Таблица обработки с датой/временем:")
        print("-" * 30)
        viewer.show_processing_table(3)
        
        print("\n🔍 4. Поиск событий:")
        print("-" * 30)
        viewer.search_events("Эл", 2)
        
        print("\n✅ Демонстрация завершена!")
        print("\n💡 Для интерактивного режима запустите:")
        print("   python tools/db_interactive.py")
        print("\n📋 Доступные команды:")
        print("   1 - stats     - Общая статистика")
        print("   2 - state     - Состояние системы")
        print("   3 - events    - Обработанные события")
        print("   4 - media     - Обработанные медиа файлы")
        print("   5 - trans     - Обработанные транскрипции")
        print("   6 - notion    - Синхронизация с Notion")
        print("   7 - table     - Таблица обработки событий")
        print("   8 - detail    - Детальная таблица с временными метками")
        print("   9 - raw       - Сырое состояние цикла")
        print("   0 - search    - Поиск событий")
        print("   h - help      - Показать справку")
        print("   q - quit/exit - Выход")
        
    finally:
        viewer.disconnect()

if __name__ == '__main__':
    demo_interactive_features()
