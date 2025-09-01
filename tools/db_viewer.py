#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Консольный viewer для просмотра данных в SQLite базе состояния системы.
"""

import sqlite3
import json
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class DatabaseViewer:
    """Консольный viewer для SQLite базы данных."""
    
    def __init__(self, db_path: str = "data/system_state.db"):
        """
        Инициализация viewer.
        
        Args:
            db_path: Путь к базе данных SQLite
        """
        self.db_path = db_path
        self.conn = None
    
    def connect(self) -> bool:
        """Подключение к базе данных."""
        try:
            if not Path(self.db_path).exists():
                print(f"❌ База данных не найдена: {self.db_path}")
                return False
            
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row  # Для доступа по именам колонок
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к базе данных: {e}")
            return False
    
    def disconnect(self):
        """Отключение от базы данных."""
        if self.conn:
            self.conn.close()
    
    def show_tables(self):
        """Показывает все таблицы в базе данных."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print("📋 Таблицы в базе данных:")
            for table in tables:
                print(f"  • {table[0]}")
            
        except Exception as e:
            print(f"❌ Ошибка получения списка таблиц: {e}")
    
    def show_system_state(self, limit: int = 10):
        """Показывает состояние системы."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT cycle_id, timestamp, personal_events_processed, work_events_processed,
                       media_processed, transcriptions_processed, notion_synced, errors_count,
                       personal_status, work_status, media_status, transcription_status, notion_status,
                       execution_time, created_at
                FROM system_state 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            
            states = cursor.fetchall()
            
            if not states:
                print("📊 Состояния системы не найдены")
                return
            
            print(f"📊 Последние {len(states)} состояний системы:")
            print("=" * 120)
            
            for state in states:
                print(f"🔄 Цикл #{state['cycle_id']} - {state['timestamp']}")
                print(f"   📅 События: личные={state['personal_events_processed']}, рабочие={state['work_events_processed']}")
                print(f"   🎬 Медиа: {state['media_processed']}, 🎤 Транскрипции: {state['transcriptions_processed']}")
                print(f"   📝 Notion: {state['notion_synced']}, ❌ Ошибки: {state['errors_count']}")
                print(f"   📊 Статусы: personal={state['personal_status']}, work={state['work_status']}, media={state['media_status']}")
                print(f"   ⏱️ Время выполнения: {state['execution_time']:.2f}с, создано: {state['created_at']}")
                print("-" * 120)
            
        except Exception as e:
            print(f"❌ Ошибка получения состояния системы: {e}")
    
    def show_processed_events(self, limit: int = 20, account_type: Optional[str] = None):
        """Показывает обработанные события календаря."""
        try:
            cursor = self.conn.cursor()
            
            if account_type:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    WHERE account_type = ?
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (account_type, limit))
            else:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (limit,))
            
            events = cursor.fetchall()
            
            if not events:
                print("📅 Обработанные события не найдены")
                return
            
            print(f"📅 Последние {len(events)} обработанных событий:")
            if account_type:
                print(f"   (фильтр: {account_type})")
            print("=" * 100)
            
            for event in events:
                print(f"🆔 {event['event_id']}")
                print(f"   👤 Аккаунт: {event['account_type']}")
                print(f"   📝 Название: {event['event_title']}")
                if event['event_start_time']:
                    print(f"   📅 Начало: {event['event_start_time']}")
                if event['event_end_time']:
                    print(f"   📅 Окончание: {event['event_end_time']}")
                print(f"   ⏰ Обработано: {event['processed_at']}")
                print("-" * 100)
            
        except Exception as e:
            print(f"❌ Ошибка получения обработанных событий: {e}")
    
    def show_processed_media(self, limit: int = 20):
        """Показывает обработанные медиа файлы."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT file_path, file_hash, status, processed_at
                FROM processed_media 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (limit,))
            
            media = cursor.fetchall()
            
            if not media:
                print("🎬 Обработанные медиа файлы не найдены")
                return
            
            print(f"🎬 Последние {len(media)} обработанных медиа файлов:")
            print("=" * 120)
            
            for file in media:
                print(f"📁 {file['file_path']}")
                print(f"   🔑 Хеш: {file['file_hash'][:16]}..." if file['file_hash'] else "   🔑 Хеш: не указан")
                print(f"   📊 Статус: {file['status']}")
                print(f"   ⏰ Обработано: {file['processed_at']}")
                print("-" * 120)
            
        except Exception as e:
            print(f"❌ Ошибка получения обработанных медиа файлов: {e}")
    
    def show_processed_transcriptions(self, limit: int = 20):
        """Показывает обработанные транскрипции."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT file_path, status, processed_at
                FROM processed_transcriptions 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (limit,))
            
            transcriptions = cursor.fetchall()
            
            if not transcriptions:
                print("🎤 Обработанные транскрипции не найдены")
                return
            
            print(f"🎤 Последние {len(transcriptions)} обработанных транскрипций:")
            print("=" * 100)
            
            for trans in transcriptions:
                print(f"📄 {trans['file_path']}")
                print(f"   📊 Статус: {trans['status']}")
                print(f"   ⏰ Обработано: {trans['processed_at']}")
                print("-" * 100)
            
        except Exception as e:
            print(f"❌ Ошибка получения обработанных транскрипций: {e}")
    
    def show_notion_sync(self, limit: int = 20):
        """Показывает синхронизацию с Notion."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT page_id, event_id, status, last_sync
                FROM notion_sync 
                ORDER BY last_sync DESC 
                LIMIT ?
            ''', (limit,))
            
            syncs = cursor.fetchall()
            
            if not syncs:
                print("📝 Синхронизация с Notion не найдена")
                return
            
            print(f"📝 Последние {len(syncs)} синхронизаций с Notion:")
            print("=" * 100)
            
            for sync in syncs:
                print(f"📄 Page ID: {sync['page_id']}")
                print(f"   🆔 Event ID: {sync['event_id']}")
                print(f"   📊 Статус: {sync['status']}")
                print(f"   ⏰ Последняя синхронизация: {sync['last_sync']}")
                print("-" * 100)
            
        except Exception as e:
            print(f"❌ Ошибка получения синхронизации с Notion: {e}")
    
    def show_statistics(self):
        """Показывает общую статистику."""
        try:
            cursor = self.conn.cursor()
            
            # Общая статистика
            cursor.execute('SELECT COUNT(*) FROM system_state')
            total_cycles = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM processed_events')
            total_events = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM processed_media')
            total_media = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM processed_transcriptions')
            total_transcriptions = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM notion_sync')
            total_notion_sync = cursor.fetchone()[0]
            
            # Статистика по аккаунтам
            cursor.execute('SELECT account_type, COUNT(*) FROM processed_events GROUP BY account_type')
            events_by_account = cursor.fetchall()
            
            # Последний цикл
            cursor.execute('''
                SELECT cycle_id, timestamp, personal_events_processed, work_events_processed,
                       media_processed, transcriptions_processed, notion_synced, errors_count
                FROM system_state 
                ORDER BY created_at DESC LIMIT 1
            ''')
            
            last_cycle = cursor.fetchone()
            
            print("📊 ОБЩАЯ СТАТИСТИКА")
            print("=" * 50)
            print(f"🔄 Всего циклов обработки: {total_cycles}")
            print(f"📅 Всего обработанных событий: {total_events}")
            print(f"🎬 Всего обработанных медиа файлов: {total_media}")
            print(f"🎤 Всего обработанных транскрипций: {total_transcriptions}")
            print(f"📝 Всего синхронизаций с Notion: {total_notion_sync}")
            
            if events_by_account:
                print("\n📅 События по аккаунтам:")
                for account, count in events_by_account:
                    print(f"   {account}: {count}")
            
            if last_cycle:
                print(f"\n🔄 Последний цикл #{last_cycle['cycle_id']} ({last_cycle['timestamp']}):")
                print(f"   📅 События: личные={last_cycle['personal_events_processed']}, рабочие={last_cycle['work_events_processed']}")
                print(f"   🎬 Медиа: {last_cycle['media_processed']}, 🎤 Транскрипции: {last_cycle['transcriptions_processed']}")
                print(f"   📝 Notion: {last_cycle['notion_synced']}, ❌ Ошибки: {last_cycle['errors_count']}")
            
        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
    
    def show_raw_state(self, cycle_id: int):
        """Показывает сырое состояние для конкретного цикла."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT raw_state FROM system_state WHERE cycle_id = ?
            ''', (cycle_id,))
            
            result = cursor.fetchone()
            
            if not result:
                print(f"❌ Цикл #{cycle_id} не найден")
                return
            
            raw_state = json.loads(result['raw_state'])
            
            print(f"🔍 Сырое состояние цикла #{cycle_id}:")
            print("=" * 50)
            print(json.dumps(raw_state, indent=2, ensure_ascii=False))
            
        except Exception as e:
            print(f"❌ Ошибка получения сырого состояния: {e}")
    
    def search_events(self, query: str, limit: int = 10):
        """Поиск событий по названию."""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                FROM processed_events 
                WHERE event_title LIKE ?
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (f'%{query}%', limit))
            
            events = cursor.fetchall()
            
            if not events:
                print(f"🔍 События с запросом '{query}' не найдены")
                return
            
            print(f"🔍 Найдено {len(events)} событий с запросом '{query}':")
            print("=" * 100)
            
            for event in events:
                print(f"🆔 {event['event_id']}")
                print(f"   👤 Аккаунт: {event['account_type']}")
                print(f"   📝 Название: {event['event_title']}")
                if event['event_start_time']:
                    print(f"   📅 Начало: {event['event_start_time']}")
                if event['event_end_time']:
                    print(f"   📅 Окончание: {event['event_end_time']}")
                print(f"   ⏰ Обработано: {event['processed_at']}")
                print("-" * 100)
            
        except Exception as e:
            print(f"❌ Ошибка поиска событий: {e}")
    
    def show_processing_table(self, limit: int = 20):
        """Показывает таблицу обработки событий."""
        try:
            cursor = self.conn.cursor()
            
            # Получаем все события
            cursor.execute('''
                SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                FROM processed_events 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (limit,))
            
            events = cursor.fetchall()
            
            if not events:
                print("📊 События для таблицы не найдены")
                return
            
            print(f"📊 ТАБЛИЦА ОБРАБОТКИ СОБЫТИЙ (последние {len(events)} событий)")
            print("=" * 150)
            
            # Заголовок таблицы
            header = f"{'Событие':<40} {'Дата/Время':<20} {'Аккаунт':<8} {'Календарь':<12} {'Медиа':<12} {'Транскрипция':<15} {'Notion':<12} {'Статус':<10}"
            print(header)
            print("-" * 170)
            
            for event in events:
                event_id = event['event_id']
                account_type = event['account_type']
                event_title = event['event_title'][:37] + "..." if len(event['event_title']) > 40 else event['event_title']
                
                # Форматируем дату и время
                event_datetime = ""
                if event['event_start_time']:
                    try:
                        # Парсим ISO формат и форматируем для отображения
                        from datetime import datetime
                        dt = datetime.fromisoformat(event['event_start_time'].replace('Z', '+00:00'))
                        event_datetime = dt.strftime('%Y-%m-%d %H:%M')
                    except:
                        event_datetime = event['event_start_time'][:16] if len(event['event_start_time']) > 16 else event['event_start_time']
                
                # Проверяем статус обработки для каждого этапа
                calendar_status = "✅" if event['processed_at'] else "❌"
                
                # Проверяем медиа файлы
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_media 
                    WHERE file_path LIKE ?
                ''', (f'%{event_id}%',))
                media_count = cursor.fetchone()[0]
                media_status = f"✅({media_count})" if media_count > 0 else "❌"
                
                # Проверяем транскрипции
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_transcriptions 
                    WHERE file_path LIKE ?
                ''', (f'%{event_id}%',))
                trans_count = cursor.fetchone()[0]
                trans_status = f"✅({trans_count})" if trans_count > 0 else "❌"
                
                # Проверяем синхронизацию с Notion
                cursor.execute('''
                    SELECT COUNT(*) FROM notion_sync 
                    WHERE event_id = ?
                ''', (event_id,))
                notion_count = cursor.fetchone()[0]
                notion_status = f"✅({notion_count})" if notion_count > 0 else "❌"
                
                # Определяем общий статус
                if media_count > 0 and trans_count > 0 and notion_count > 0:
                    overall_status = "✅ Полный"
                elif media_count > 0 or trans_count > 0 or notion_count > 0:
                    overall_status = "🔄 Частичный"
                else:
                    overall_status = "❌ Только календарь"
                
                # Формируем строку таблицы
                row = f"{event_title:<40} {event_datetime:<20} {account_type:<8} {calendar_status:<12} {media_status:<12} {trans_status:<15} {notion_status:<12} {overall_status:<10}"
                print(row)
            
            print("-" * 150)
            print("📝 Легенда:")
            print("  ✅ - Обработано")
            print("  ❌ - Не обработано")
            print("  (число) - Количество обработанных файлов")
            print("  Полный - Все этапы выполнены")
            print("  Частичный - Выполнены некоторые этапы")
            print("  Только календарь - Создано только событие в календаре")
            
        except Exception as e:
            print(f"❌ Ошибка создания таблицы обработки: {e}")
    
    def show_detailed_processing_table(self, limit: int = 10):
        """Показывает детальную таблицу обработки с временными метками."""
        try:
            cursor = self.conn.cursor()
            
            # Получаем все события
            cursor.execute('''
                SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                FROM processed_events 
                ORDER BY processed_at DESC 
                LIMIT ?
            ''', (limit,))
            
            events = cursor.fetchall()
            
            if not events:
                print("📊 События для детальной таблицы не найдены")
                return
            
            print(f"📊 ДЕТАЛЬНАЯ ТАБЛИЦА ОБРАБОТКИ (последние {len(events)} событий)")
            print("=" * 180)
            
            # Заголовок таблицы
            header = f"{'Событие':<40} {'Аккаунт':<8} {'Календарь':<20} {'Медиа':<20} {'Транскрипция':<20} {'Notion':<20} {'Статус':<10}"
            print(header)
            print("-" * 180)
            
            for event in events:
                event_id = event['event_id']
                account_type = event['account_type']
                event_title = event['event_title'][:37] + "..." if len(event['event_title']) > 40 else event['event_title']
                
                # Время обработки календаря
                calendar_time = event['processed_at'][:16] if event['processed_at'] else "❌"
                
                # Проверяем медиа файлы с временными метками
                cursor.execute('''
                    SELECT processed_at FROM processed_media 
                    WHERE file_path LIKE ? 
                    ORDER BY processed_at DESC LIMIT 1
                ''', (f'%{event_id}%',))
                media_result = cursor.fetchone()
                media_time = media_result[0][:16] if media_result else "❌"
                
                # Проверяем транскрипции с временными метками
                cursor.execute('''
                    SELECT processed_at FROM processed_transcriptions 
                    WHERE file_path LIKE ? 
                    ORDER BY processed_at DESC LIMIT 1
                ''', (f'%{event_id}%',))
                trans_result = cursor.fetchone()
                trans_time = trans_result[0][:16] if trans_result else "❌"
                
                # Проверяем синхронизацию с Notion с временными метками
                cursor.execute('''
                    SELECT last_sync FROM notion_sync 
                    WHERE event_id = ? 
                    ORDER BY last_sync DESC LIMIT 1
                ''', (event_id,))
                notion_result = cursor.fetchone()
                notion_time = notion_result[0][:16] if notion_result else "❌"
                
                # Определяем общий статус
                completed_stages = sum([
                    1 if calendar_time != "❌" else 0,
                    1 if media_time != "❌" else 0,
                    1 if trans_time != "❌" else 0,
                    1 if notion_time != "❌" else 0
                ])
                
                if completed_stages == 4:
                    overall_status = "✅ Полный"
                elif completed_stages > 1:
                    overall_status = f"🔄 {completed_stages}/4"
                else:
                    overall_status = "❌ Только календарь"
                
                # Формируем строку таблицы
                row = f"{event_title:<40} {account_type:<8} {calendar_time:<20} {media_time:<20} {trans_time:<20} {notion_time:<20} {overall_status:<10}"
                print(row)
            
            print("-" * 180)
            print("📝 Легенда:")
            print("  ✅ - Обработано")
            print("  ❌ - Не обработано")
            print("  YYYY-MM-DD HH:MM - Время обработки")
            print("  Полный - Все 4 этапа выполнены")
            print("  X/4 - Выполнено X из 4 этапов")
            print("  Только календарь - Создано только событие в календаре")
            
        except Exception as e:
            print(f"❌ Ошибка создания детальной таблицы обработки: {e}")
    
    def clear_database(self, confirm: bool = False):
        """Очищает всю базу данных."""
        if not confirm:
            print("⚠️  ВНИМАНИЕ: Эта операция удалит ВСЕ данные из базы!")
            print("📋 Будут удалены:")
            print("   • Все состояния системы")
            print("   • Все обработанные события")
            print("   • Все обработанные медиа файлы")
            print("   • Все обработанные транскрипции")
            print("   • Все синхронизации с Notion")
            print()
            response = input("❓ Вы уверены? Введите 'YES' для подтверждения: ").strip()
            if response != 'YES':
                print("❌ Операция отменена")
                return False
        
        try:
            cursor = self.conn.cursor()
            
            # Получаем статистику перед удалением
            tables = ['system_state', 'processed_events', 'processed_media', 'processed_transcriptions', 'notion_sync']
            stats = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            
            print("📊 Статистика перед очисткой:")
            for table, count in stats.items():
                print(f"   • {table}: {count} записей")
            
            # Удаляем все данные
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            
            # Сбрасываем автоинкремент
            cursor.execute("DELETE FROM sqlite_sequence")
            
            self.conn.commit()
            
            print("✅ База данных успешно очищена")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка очистки базы данных: {e}")
            self.conn.rollback()
            return False
    
    def delete_event(self, event_id: str, account_type: str = None, confirm: bool = False):
        """Удаляет конкретное событие из базы данных."""
        try:
            cursor = self.conn.cursor()
            
            # Сначала найдем событие
            if account_type:
                cursor.execute("""
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    WHERE event_id = ? AND account_type = ?
                """, (event_id, account_type))
            else:
                cursor.execute("""
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    WHERE event_id = ?
                """, (event_id,))
            
            events = cursor.fetchall()
            
            if not events:
                print(f"❌ Событие с ID '{event_id}' не найдено")
                return False
            
            if len(events) > 1:
                print(f"🔍 Найдено {len(events)} событий с ID '{event_id}':")
                for i, event in enumerate(events, 1):
                    print(f"   {i}. {event['account_type']} - {event['event_title']} ({event['event_start_time']})")
                print()
                choice = input("❓ Введите номер события для удаления (или 'all' для всех): ").strip()
                
                if choice.lower() == 'all':
                    events_to_delete = events
                else:
                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(events):
                            events_to_delete = [events[idx]]
                        else:
                            print("❌ Неверный номер события")
                            return False
                    except ValueError:
                        print("❌ Неверный ввод")
                        return False
            else:
                events_to_delete = events
            
            # Показываем информацию о событиях для удаления
            print("📋 События для удаления:")
            for event in events_to_delete:
                print(f"   • {event['event_id']} ({event['account_type']})")
                print(f"     Название: {event['event_title']}")
                print(f"     Время: {event['event_start_time']} - {event['event_end_time']}")
                print(f"     Обработано: {event['processed_at']}")
                print()
            
            if not confirm:
                response = input("❓ Удалить эти события? Введите 'YES' для подтверждения: ").strip()
                if response != 'YES':
                    print("❌ Операция отменена")
                    return False
            
            # Удаляем события
            deleted_count = 0
            for event in events_to_delete:
                cursor.execute("""
                    DELETE FROM processed_events 
                    WHERE event_id = ? AND account_type = ?
                """, (event['event_id'], event['account_type']))
                deleted_count += cursor.rowcount
            
            self.conn.commit()
            print(f"✅ Удалено {deleted_count} событий")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка удаления события: {e}")
            self.conn.rollback()
            return False
    
    def list_events_for_deletion(self, limit: int = 20):
        """Показывает список событий для выбора удаления."""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                FROM processed_events 
                ORDER BY processed_at DESC 
                LIMIT ?
            """, (limit,))
            
            events = cursor.fetchall()
            
            if not events:
                print("📭 Нет событий для удаления")
                return
            
            print(f"📋 Список событий для удаления (последние {len(events)}):")
            print("=" * 120)
            print(f"{'№':<3} {'ID':<25} {'Аккаунт':<8} {'Название':<40} {'Время':<20} {'Обработано':<20}")
            print("-" * 120)
            
            for i, event in enumerate(events, 1):
                event_id = event['event_id'][:22] + "..." if len(event['event_id']) > 25 else event['event_id']
                event_title = event['event_title'][:37] + "..." if len(event['event_title']) > 40 else event['event_title']
                event_time = event['event_start_time'][:16] if event['event_start_time'] else "N/A"
                processed_time = event['processed_at'][:16] if event['processed_at'] else "N/A"
                
                print(f"{i:<3} {event_id:<25} {event['account_type']:<8} {event_title:<40} {event_time:<20} {processed_time:<20}")
            
            print("=" * 120)
            print("💡 Используйте команду 'delete-event <номер>' для удаления конкретного события")
            
        except Exception as e:
            print(f"❌ Ошибка получения списка событий: {e}")


def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Консольный viewer для SQLite базы данных состояния системы')
    parser.add_argument('--db', default='data/system_state.db', help='Путь к базе данных')
    parser.add_argument('--limit', type=int, default=10, help='Количество записей для показа')
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда для показа таблиц
    subparsers.add_parser('tables', help='Показать все таблицы')
    
    # Команда для показа состояния системы
    state_parser = subparsers.add_parser('state', help='Показать состояние системы')
    state_parser.add_argument('--limit', type=int, default=10, help='Количество записей')
    
    # Команда для показа событий
    events_parser = subparsers.add_parser('events', help='Показать обработанные события')
    events_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    events_parser.add_argument('--account', choices=['personal', 'work'], help='Фильтр по типу аккаунта')
    
    # Команда для показа медиа
    media_parser = subparsers.add_parser('media', help='Показать обработанные медиа файлы')
    media_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для показа транскрипций
    trans_parser = subparsers.add_parser('transcriptions', help='Показать обработанные транскрипции')
    trans_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для показа синхронизации с Notion
    notion_parser = subparsers.add_parser('notion', help='Показать синхронизацию с Notion')
    notion_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для показа статистики
    subparsers.add_parser('stats', help='Показать общую статистику')
    
    # Команда для показа сырого состояния
    raw_parser = subparsers.add_parser('raw', help='Показать сырое состояние цикла')
    raw_parser.add_argument('cycle_id', type=int, help='ID цикла')
    
    # Команда для поиска событий
    search_parser = subparsers.add_parser('search', help='Поиск событий по названию')
    search_parser.add_argument('query', help='Поисковый запрос')
    search_parser.add_argument('--limit', type=int, default=10, help='Количество записей')
    
    # Команда для таблицы обработки
    table_parser = subparsers.add_parser('table', help='Показать таблицу обработки событий')
    table_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для детальной таблицы обработки
    detail_parser = subparsers.add_parser('detail', help='Показать детальную таблицу обработки с временными метками')
    detail_parser.add_argument('--limit', type=int, default=10, help='Количество записей')
    
    # Команда для очистки базы данных
    clear_parser = subparsers.add_parser('clear', help='Очистить всю базу данных')
    clear_parser.add_argument('--force', action='store_true', help='Принудительная очистка без подтверждения')
    
    # Команда для удаления события
    delete_parser = subparsers.add_parser('delete-event', help='Удалить конкретное событие')
    delete_parser.add_argument('event_id', help='ID события для удаления')
    delete_parser.add_argument('--account', choices=['personal', 'work'], help='Тип аккаунта (если не указан, удаляются все совпадения)')
    delete_parser.add_argument('--force', action='store_true', help='Принудительное удаление без подтверждения')
    
    # Команда для списка событий для удаления
    list_parser = subparsers.add_parser('list-events', help='Показать список событий для удаления')
    list_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для обновления данных
    subparsers.add_parser('refresh', help='Обновить данные из базы данных')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Создаем viewer
    viewer = DatabaseViewer(args.db)
    
    if not viewer.connect():
        return
    
    try:
        # Выполняем команду
        if args.command == 'tables':
            viewer.show_tables()
        
        elif args.command == 'state':
            viewer.show_system_state(args.limit)
        
        elif args.command == 'events':
            viewer.show_processed_events(args.limit, args.account)
        
        elif args.command == 'media':
            viewer.show_processed_media(args.limit)
        
        elif args.command == 'transcriptions':
            viewer.show_processed_transcriptions(args.limit)
        
        elif args.command == 'notion':
            viewer.show_notion_sync(args.limit)
        
        elif args.command == 'stats':
            viewer.show_statistics()
        
        elif args.command == 'raw':
            viewer.show_raw_state(args.cycle_id)
        
        elif args.command == 'search':
            viewer.search_events(args.query, args.limit)
        
        elif args.command == 'table':
            viewer.show_processing_table(args.limit)
        
        elif args.command == 'detail':
            viewer.show_detailed_processing_table(args.limit)
        
        elif args.command == 'clear':
            viewer.clear_database(confirm=args.force)
        
        elif args.command == 'delete-event':
            viewer.delete_event(args.event_id, args.account, confirm=args.force)
        
        elif args.command == 'list-events':
            viewer.list_events_for_deletion(args.limit)
        
        elif args.command == 'refresh':
            print("🔄 Обновление данных из базы данных...")
            viewer.disconnect()
            if viewer.connect():
                print("✅ Подключение к базе данных обновлено")
                print("\n📊 Обновленная статистика:")
                viewer.show_statistics()
                print("\n📋 Обновленная таблица обработки:")
                viewer.show_processing_table(20)
            else:
                print("❌ Не удалось переподключиться к базе данных")
    
    finally:
        viewer.disconnect()


if __name__ == '__main__':
    main()
