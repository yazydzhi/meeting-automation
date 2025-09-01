#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интерактивный режим для просмотра данных в SQLite базе.
"""

import sys
import os
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

from tools.db_viewer import DatabaseViewer


class InteractiveDBViewer:
    """Интерактивный viewer для базы данных."""
    
    def __init__(self, db_path: str = "data/system_state.db"):
        self.viewer = DatabaseViewer(db_path)
        self.running = True
    
    def start(self):
        """Запуск интерактивного режима."""
        if not self.viewer.connect():
            return
        
        print("🔍 Интерактивный DB Viewer")
        print("=" * 50)
        print("Доступные команды:")
        print("  1 - stats     - Общая статистика")
        print("  2 - state     - Состояние системы")
        print("  3 - events    - Обработанные события")
        print("  4 - media     - Обработанные медиа файлы")
        print("  5 - trans     - Обработанные транскрипции")
        print("  6 - notion    - Синхронизация с Notion")
        print("  7 - table     - Таблица обработки событий")
        print("  8 - detail    - Детальная таблица с временными метками")
        print("  9 - raw       - Сырое состояние цикла")
        print("  0 - search    - Поиск событий")
        print("  h - help      - Показать справку")
        print("  q - quit/exit - Выход")
        print("=" * 50)
        print("💡 После отображения данных нажмите Enter для возврата в меню")
        
        while self.running:
            try:
                command = input("\n🔍 > ").strip()
                
                # Обработка числовых команд
                if command == '1':
                    self.viewer.show_statistics()
                    self._wait_for_return()
                elif command == '2':
                    self.viewer.show_system_state(10)
                    self._wait_for_return()
                elif command == '3':
                    self.viewer.show_processed_events(20)
                    self._wait_for_return()
                elif command == '4':
                    self.viewer.show_processed_media(20)
                    self._wait_for_return()
                elif command == '5':
                    self.viewer.show_processed_transcriptions(20)
                    self._wait_for_return()
                elif command == '6':
                    self.viewer.show_notion_sync(20)
                    self._wait_for_return()
                elif command == '7':
                    self.viewer.show_processing_table(20)
                    self._wait_for_return()
                elif command == '8':
                    self.viewer.show_detailed_processing_table(10)
                    self._wait_for_return()
                elif command == '9':
                    self._handle_raw_command()
                elif command == '0':
                    self._handle_search_command()
                
                # Обработка буквенных команд
                elif command.lower() in ['quit', 'exit', 'q']:
                    self.running = False
                elif command.lower() in ['help', 'h']:
                    self.show_help()
                    self._wait_for_return()
                
                # Обработка старых команд для совместимости
                elif command.lower() == 'stats':
                    self.viewer.show_statistics()
                    self._wait_for_return()
                elif command.lower() == 'state':
                    self.viewer.show_system_state(10)
                    self._wait_for_return()
                elif command.lower() == 'events':
                    self.viewer.show_processed_events(20)
                    self._wait_for_return()
                elif command.lower() == 'media':
                    self.viewer.show_processed_media(20)
                    self._wait_for_return()
                elif command.lower() == 'trans':
                    self.viewer.show_processed_transcriptions(20)
                    self._wait_for_return()
                elif command.lower() == 'notion':
                    self.viewer.show_notion_sync(20)
                    self._wait_for_return()
                elif command.lower() == 'table':
                    self.viewer.show_processing_table(20)
                    self._wait_for_return()
                elif command.lower() == 'detail':
                    self.viewer.show_detailed_processing_table(10)
                    self._wait_for_return()
                elif command.startswith('search '):
                    query = command[7:].strip()
                    if query:
                        self.viewer.search_events(query, 10)
                        self._wait_for_return()
                    else:
                        print("❌ Укажите поисковый запрос")
                elif command.startswith('raw '):
                    try:
                        cycle_id = int(command[4:].strip())
                        self.viewer.show_raw_state(cycle_id)
                        self._wait_for_return()
                    except ValueError:
                        print("❌ Укажите корректный ID цикла")
                elif command == '':
                    continue
                else:
                    print(f"❌ Неизвестная команда: {command}")
                    print("Введите 'h' для справки или число от 0 до 9")
            
            except KeyboardInterrupt:
                print("\n👋 До свидания!")
                self.running = False
            except Exception as e:
                print(f"❌ Ошибка: {e}")
        
        self.viewer.disconnect()
    
    def _wait_for_return(self):
        """Ожидает нажатия Enter для возврата в меню."""
        try:
            input("\n⏎ Нажмите Enter для возврата в меню...")
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            self.running = False
    
    def _handle_search_command(self):
        """Обрабатывает команду поиска."""
        try:
            query = input("🔍 Введите поисковый запрос: ").strip()
            if query:
                self.viewer.search_events(query, 10)
                self._wait_for_return()
            else:
                print("❌ Поисковый запрос не может быть пустым")
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            self.running = False
    
    def _handle_raw_command(self):
        """Обрабатывает команду просмотра сырого состояния."""
        try:
            cycle_id = input("🔍 Введите ID цикла: ").strip()
            if cycle_id.isdigit():
                self.viewer.show_raw_state(int(cycle_id))
                self._wait_for_return()
            else:
                print("❌ ID цикла должен быть числом")
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            self.running = False
    
    def show_help(self):
        """Показывает справку."""
        print("\n📖 СПРАВКА")
        print("=" * 50)
        print("Числовые команды:")
        print("  1 - stats     - Общая статистика")
        print("  2 - state     - Состояние системы")
        print("  3 - events    - Обработанные события")
        print("  4 - media     - Обработанные медиа файлы")
        print("  5 - trans     - Обработанные транскрипции")
        print("  6 - notion    - Синхронизация с Notion")
        print("  7 - table     - Таблица обработки событий")
        print("  8 - detail    - Детальная таблица с временными метками")
        print("  9 - raw       - Сырое состояние цикла")
        print("  0 - search    - Поиск событий")
        print("\nБуквенные команды:")
        print("  h - help      - Показать эту справку")
        print("  q - quit/exit - Выход из программы")
        print("\n💡 После отображения данных нажмите Enter для возврата в меню")


def main():
    """Главная функция."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Интерактивный viewer для SQLite базы данных')
    parser.add_argument('--db', default='data/system_state.db', help='Путь к базе данных')
    
    args = parser.parse_args()
    
    # Проверяем существование базы данных
    if not Path(args.db).exists():
        print(f"❌ База данных не найдена: {args.db}")
        print("Убедитесь, что сервис был запущен хотя бы один раз")
        return
    
    # Запускаем интерактивный режим
    viewer = InteractiveDBViewer(args.db)
    viewer.start()


if __name__ == '__main__':
    main()
