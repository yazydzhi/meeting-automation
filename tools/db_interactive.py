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
        print("  s - summaries - Обработанные саммари")
        print("  n - notion-sync - Статус синхронизации с Notion")
        print("  f - folders   - Статус создания папок")
        print("  l - list      - Список событий для удаления")
        print("  d - delete    - Удалить событие")
        print("  c - clear     - Очистить базу данных")
        print("  r - refresh   - Обновить данные из БД")
        print("  h - help      - Показать справку")
        print("  q - quit/exit - Выход")
        print("=" * 50)
        print("💡 После отображения данных нажмите Enter для возврата в меню или 'r' для обновления")
        
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
                elif command.lower() == 'l':
                    self.viewer.list_events_for_deletion(20)
                    self._wait_for_return()
                elif command.lower() == 'd':
                    self._handle_delete_command()
                elif command.lower() == 'c':
                    self._handle_clear_command()
                elif command.lower() == 'r':
                    self._handle_refresh_command()
                elif command.lower() == 's':
                    self.viewer.show_processed_summaries(20)
                    self._wait_for_return()
                elif command.lower() == 'n':
                    self.viewer.show_notion_sync_status(20)
                    self._wait_for_return()
                elif command.lower() == 'f':
                    self.viewer.show_folder_creation_status(20)
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
                elif command.lower() == 'summaries':
                    self.viewer.show_processed_summaries(20)
                    self._wait_for_return()
                elif command.lower() == 'notion-sync':
                    self.viewer.show_notion_sync_status(20)
                    self._wait_for_return()
                elif command.lower() == 'folders':
                    self.viewer.show_folder_creation_status(20)
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
        """Ожидает нажатия Enter для возврата в меню или 'r' для обновления."""
        try:
            response = input("\n⏎ Нажмите Enter для возврата в меню или 'r' для обновления данных...").strip()
            if response.lower() == 'r':
                self._handle_refresh_command()
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
        print("  s - summaries - Обработанные саммари")
        print("  n - notion-sync - Статус синхронизации с Notion")
        print("  f - folders   - Статус создания папок")
        print("  h - help      - Показать эту справку")
        print("  q - quit/exit - Выход из программы")
        print("  l - list      - Список событий для удаления")
        print("  d - delete    - Удалить событие")
        print("  c - clear     - Очистить базу данных")
        print("  r - refresh   - Обновить данные из БД")
        print("\n💡 После отображения данных нажмите Enter для возврата в меню")
    
    def _handle_delete_command(self):
        """Обработка команды удаления события."""
        print("\n🗑️  УДАЛЕНИЕ СОБЫТИЯ")
        print("=" * 30)
        
        # Сначала показываем список событий
        self.viewer.list_events_for_deletion(20)
        print()
        
        # Запрашиваем ID события
        event_id = input("❓ Введите ID события для удаления (или 'back' для возврата): ").strip()
        
        if event_id.lower() == 'back':
            return
        
        if not event_id:
            print("❌ ID события не может быть пустым")
            return
        
        # Запрашиваем тип аккаунта (опционально)
        account_type = input("❓ Введите тип аккаунта (personal/work) или оставьте пустым для всех: ").strip()
        if account_type and account_type not in ['personal', 'work']:
            print("❌ Неверный тип аккаунта. Используйте 'personal' или 'work'")
            return
        
        # Удаляем событие
        if account_type:
            self.viewer.delete_event(event_id, account_type)
        else:
            self.viewer.delete_event(event_id)
        
        self._wait_for_return()
    
    def _handle_clear_command(self):
        """Обработка команды очистки базы данных."""
        print("\n🧹 ОЧИСТКА БАЗЫ ДАННЫХ")
        print("=" * 30)
        print("⚠️  ВНИМАНИЕ: Эта операция удалит ВСЕ данные из базы!")
        print()
        
        # Показываем текущую статистику
        self.viewer.show_statistics()
        print()
        
        # Запрашиваем подтверждение
        response = input("❓ Вы уверены? Введите 'YES' для подтверждения: ").strip()
        if response != 'YES':
            print("❌ Операция отменена")
            self._wait_for_return()
            return
        
        # Очищаем базу данных
        self.viewer.clear_database(confirm=True)
        self._wait_for_return()
    
    def _handle_refresh_command(self):
        """Обработка команды обновления данных из БД."""
        print("\n🔄 ОБНОВЛЕНИЕ ДАННЫХ ИЗ БД")
        print("=" * 35)
        
        try:
            # Переподключаемся к базе данных
            self.viewer.disconnect()
            if self.viewer.connect():
                print("✅ Подключение к базе данных обновлено")
                
                # Показываем обновленную статистику
                print("\n📊 Обновленная статистика:")
                self.viewer.show_statistics()
                
                print("\n📋 Обновленная таблица обработки:")
                self.viewer.show_processing_table(20)
                
            else:
                print("❌ Не удалось переподключиться к базе данных")
                
        except Exception as e:
            print(f"❌ Ошибка обновления данных: {e}")
        
        self._wait_for_return()


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
