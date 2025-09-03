#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Консольный viewer для просмотра данных в SQLite базе состояния системы.
"""

import sqlite3
import json
import sys
import os
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
    
    def show_system_state(self, limit: int = None):
        """Показывает состояние системы."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT cycle_id, timestamp, personal_events_processed, work_events_processed,
                           media_processed, transcriptions_processed, notion_synced, errors_count,
                           personal_status, work_status, media_status, transcription_status, notion_status,
                           execution_time, created_at
                    FROM system_state 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT cycle_id, timestamp, personal_events_processed, work_events_processed,
                           media_processed, transcriptions_processed, notion_synced, errors_count,
                           personal_status, work_status, media_status, transcription_status, notion_status,
                           execution_time, created_at
                    FROM system_state 
                    ORDER BY created_at DESC
                ''')
            
            states = cursor.fetchall()
            
            if not states:
                print("📊 Состояния системы не найдены")
                return
            
            if limit:
                print(f"📊 Последние {len(states)} состояний системы:")
            else:
                print(f"📊 Все {len(states)} состояний системы:")
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
    
    def show_processed_events(self, limit: int = None, account_type: Optional[str] = None):
        """Показывает обработанные события календаря."""
        try:
            cursor = self.conn.cursor()
            
            if account_type:
                if limit:
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
                        WHERE account_type = ?
                        ORDER BY processed_at DESC
                    ''', (account_type,))
            else:
                if limit:
                    cursor.execute('''
                        SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                        FROM processed_events 
                        ORDER BY processed_at DESC 
                        LIMIT ?
                    ''', (limit,))
                else:
                    cursor.execute('''
                        SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                        FROM processed_events 
                        ORDER BY processed_at DESC
                    ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("📅 Обработанные события не найдены")
                return
            
            if limit:
                print(f"📅 Последние {len(events)} обработанных событий:")
            else:
                print(f"📅 Все {len(events)} обработанных событий:")
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
    
    def show_processed_media(self, limit: int = None):
        """Показывает обработанные медиа файлы."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT file_path, file_hash, status, processed_at
                    FROM processed_media 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT file_path, file_hash, status, processed_at
                    FROM processed_media 
                    ORDER BY processed_at DESC
                ''')
            
            media = cursor.fetchall()
            
            if not media:
                print("🎬 Обработанные медиа файлы не найдены")
                return
            
            if limit:
                print(f"🎬 Последние {len(media)} обработанных медиа файлов:")
            else:
                print(f"🎬 Все {len(media)} обработанных медиа файлов:")
            print("=" * 120)
            
            for file in media:
                print(f"📁 {file['file_path']}")
                print(f"   🔑 Хеш: {file['file_hash'][:16]}..." if file['file_hash'] else "   🔑 Хеш: не указан")
                print(f"   📊 Статус: {file['status']}")
                print(f"   ⏰ Обработано: {file['processed_at']}")
                print("-" * 120)
            
        except Exception as e:
            print(f"❌ Ошибка получения обработанных медиа файлов: {e}")
    
    def show_processed_transcriptions(self, limit: int = None):
        """Показывает обработанные транскрипции."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT file_path, status, processed_at
                    FROM processed_transcriptions 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT file_path, status, processed_at
                    FROM processed_transcriptions 
                    ORDER BY processed_at DESC
                ''')
            
            transcriptions = cursor.fetchall()
            
            if not transcriptions:
                print("🎤 Обработанные транскрипции не найдены")
                return
            
            if limit:
                print(f"🎤 Последние {len(transcriptions)} обработанных транскрипций:")
            else:
                print(f"🎤 Все {len(transcriptions)} обработанных транскрипций:")
            print("=" * 100)
            
            for trans in transcriptions:
                print(f"📄 {trans['file_path']}")
                print(f"   📊 Статус: {trans['status']}")
                print(f"   ⏰ Обработано: {trans['processed_at']}")
                print("-" * 100)
            
        except Exception as e:
            print(f"❌ Ошибка получения обработанных транскрипций: {e}")
    
    def show_notion_sync(self, limit: int = None):
        """Показывает синхронизацию с Notion."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT page_id, event_id, status, last_sync
                    FROM notion_sync 
                    ORDER BY last_sync DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT page_id, event_id, status, last_sync
                    FROM notion_sync 
                    ORDER BY last_sync DESC
                ''')
            
            syncs = cursor.fetchall()
            
            if not syncs:
                print("📝 Синхронизация с Notion не найдена")
                return
            
            if limit:
                print(f"📝 Последние {len(syncs)} синхронизаций с Notion:")
            else:
                print(f"📝 Все {len(syncs)} синхронизаций с Notion:")
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
    
    def search_events(self, query: str, limit: int = None):
        """Поиск событий по названию."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    WHERE event_title LIKE ?
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (f'%{query}%', limit))
            else:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    WHERE event_title LIKE ?
                    ORDER BY processed_at DESC
                ''', (f'%{query}%',))
            
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
    
    def show_processing_table(self, limit: int = None):
        """Показывает таблицу обработки событий."""
        try:
            cursor = self.conn.cursor()
            
            # Получаем все события
            if limit:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC
                ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("📊 События для таблицы не найдены")
                return
            
            if limit:
                print(f"📊 ТАБЛИЦА ОБРАБОТКИ СОБЫТИЙ (последние {len(events)} событий)")
            else:
                print(f"📊 ТАБЛИЦА ОБРАБОТКИ СОБЫТИЙ (все {len(events)} событий)")
            print("=" * 150)
            
            # Заголовок таблицы
            header = f"{'Событие':<40} {'Дата/Время':<20} {'Аккаунт':<8} {'Календарь':<12} {'Папка':<8} {'Notion':<8} {'Notion Content':<15} {'Медиа':<12} {'Транскрипция':<15} {'Саммари':<10} {'Статус':<10}"
            print(header)
            print("-" * 220)
            
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
                
                # Проверяем создание папки
                cursor.execute('''
                    SELECT COUNT(*) FROM folder_creation_status 
                    WHERE event_id = ? AND account_type = ? AND status = 'success'
                ''', (event_id, account_type))
                folder_count = cursor.fetchone()[0]
                folder_status = "✅" if folder_count > 0 else "❌"
                
                # Проверяем создание страницы в Notion
                cursor.execute('''
                    SELECT COUNT(*) FROM notion_sync_status 
                    WHERE event_id = ? AND sync_status = 'success'
                ''', (event_id,))
                notion_page_count = cursor.fetchone()[0]
                notion_page_status = "✅" if notion_page_count > 0 else "❌"
                
                # Проверяем синхронизацию контента в Notion
                cursor.execute('''
                    SELECT content_type, sync_status FROM notion_content_sync 
                    WHERE event_id = ?
                ''', (event_id,))
                content_sync_results = cursor.fetchall()
                
                notion_content_status = "❌"
                if content_sync_results:
                    # Проверяем, есть ли успешные синхронизации
                    success_count = sum(1 for _, status in content_sync_results if status == 'success')
                    total_count = len(content_sync_results)
                    if success_count == total_count and total_count > 0:
                        notion_content_status = f"✅({success_count})"
                    elif success_count > 0:
                        notion_content_status = f"🔄({success_count}/{total_count})"
                    else:
                        notion_content_status = "❌"
                
                # Проверяем медиа файлы - ищем по папке события
                cursor.execute('''
                    SELECT fcs.folder_path FROM folder_creation_status fcs
                    WHERE fcs.event_id = ? AND fcs.account_type = ? AND fcs.status = 'success'
                ''', (event_id, account_type))
                folder_result = cursor.fetchone()
                
                media_count = 0
                if folder_result:
                    folder_path = folder_result[0]
                    cursor.execute('''
                        SELECT COUNT(*) FROM processed_media 
                        WHERE file_path LIKE ?
                    ''', (f'{folder_path}%',))
                    media_count = cursor.fetchone()[0]
                media_status = f"✅({media_count})" if media_count > 0 else "❌"
                
                # Проверяем транскрипции - ищем по папке события
                trans_count = 0
                if folder_result:
                    folder_path = folder_result[0]
                    cursor.execute('''
                        SELECT COUNT(*) FROM processed_transcriptions 
                        WHERE file_path LIKE ?
                    ''', (f'{folder_path}%',))
                    trans_count = cursor.fetchone()[0]
                trans_status = f"✅({trans_count})" if trans_count > 0 else "❌"
                
                # Проверяем саммари - ищем по папке события
                summary_count = 0
                if folder_result:
                    folder_path = folder_result[0]
                    cursor.execute('''
                        SELECT COUNT(*) FROM processed_summaries 
                        WHERE summary_file LIKE ?
                    ''', (f'{folder_path}%',))
                    summary_count = cursor.fetchone()[0]
                summary_status = f"✅({summary_count})" if summary_count > 0 else "❌"
                
                # Определяем общий статус
                if folder_count > 0 and notion_page_count > 0 and media_count > 0 and trans_count > 0 and summary_count > 0:
                    overall_status = "✅ Полный"
                elif folder_count > 0 and notion_page_count > 0:
                    overall_status = "🔄 Базовая обработка"
                elif folder_count > 0 or notion_page_count > 0 or media_count > 0 or trans_count > 0 or summary_count > 0:
                    overall_status = "🔄 Частичный"
                else:
                    overall_status = "❌ Только календарь"
                
                # Формируем строку таблицы
                row = f"{event_title:<40} {event_datetime:<20} {account_type:<8} {calendar_status:<12} {folder_status:<8} {notion_page_status:<8} {notion_content_status:<15} {media_status:<12} {trans_status:<15} {summary_status:<10} {overall_status:<10}"
                print(row)
            
            print("-" * 220)
            print("📝 Легенда:")
            print("  ✅ - Обработано")
            print("  ❌ - Не обработано")
            print("  🔄 - Частично обработано")
            print("  (число) - Количество обработанных файлов")
            print("  Notion Content - Синхронизация контента (транскрипция/саммари) в Notion")
            print("  Полный - Все этапы выполнены (папка + Notion + медиа + транскрипция + саммари)")
            print("  Базовая обработка - Создана папка и страница в Notion")
            print("  Частичный - Выполнены некоторые этапы")
            print("  Только календарь - Создано только событие в календаре")
            
        except Exception as e:
            print(f"❌ Ошибка создания таблицы обработки: {e}")
    
    def show_detailed_processing_table(self, limit: int = None):
        """Показывает детальную таблицу обработки с временными метками."""
        try:
            cursor = self.conn.cursor()
            
            # Получаем все события
            if limit:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC
                ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("📊 События для детальной таблицы не найдены")
                return
            
            if limit:
                print(f"📊 ДЕТАЛЬНАЯ ТАБЛИЦА ОБРАБОТКИ (последние {len(events)} событий)")
            else:
                print(f"📊 ДЕТАЛЬНАЯ ТАБЛИЦА ОБРАБОТКИ (все {len(events)} событий)")
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
    
    def list_events_for_deletion(self, limit: int = None):
        """Показывает список событий для выбора удаления."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute("""
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC 
                    LIMIT ?
                """, (limit,))
            else:
                cursor.execute("""
                    SELECT event_id, account_type, event_title, event_start_time, event_end_time, processed_at
                    FROM processed_events 
                    ORDER BY processed_at DESC
                """)
            
            events = cursor.fetchall()
            
            if not events:
                print("📭 Нет событий для удаления")
                return
            
            if limit:
                print(f"📋 Список событий для удаления (последние {len(events)}):")
            else:
                print(f"📋 Список событий для удаления (все {len(events)}):")
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

    def show_processed_summaries(self, limit: int = None):
        """Показывает обработанные саммари."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT 
                        id,
                        transcript_file,
                        summary_file,
                        analysis_file,
                        status,
                        created_at
                    FROM processed_summaries 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT 
                        id,
                        transcript_file,
                        summary_file,
                        analysis_file,
                        status,
                        created_at
                    FROM processed_summaries 
                    ORDER BY created_at DESC
                ''')
            
            summaries = cursor.fetchall()
            
            if not summaries:
                print("📋 Обработанные саммари не найдены")
                return
            
            if limit:
                print(f"📋 Обработанные саммари (последние {len(summaries)}):")
            else:
                print(f"📋 Все {len(summaries)} обработанных саммари:")
            print("=" * 120)
            print(f"{'ID':<3} {'Статус':<8} {'Создано':<20} {'Файл транскрипции':<50}")
            print("=" * 120)
            
            for summary in summaries:
                transcript_name = os.path.basename(summary['transcript_file']) if summary['transcript_file'] else 'N/A'
                created_time = summary['created_at'][:19] if summary['created_at'] else 'N/A'
                
                print(f"{summary['id']:<3} {summary['status']:<8} {created_time:<20} {transcript_name:<50}")
            
            print("=" * 120)
            
        except Exception as e:
            print(f"❌ Ошибка получения саммари: {e}")

    def show_notion_sync_status(self, limit: int = None):
        """Показывает статус синхронизации с Notion."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT 
                        id,
                        event_id,
                        page_id,
                        page_url,
                        sync_status,
                        last_sync,
                        created_at
                    FROM notion_sync_status 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT 
                        id,
                        event_id,
                        page_id,
                        page_url,
                        sync_status,
                        last_sync,
                        created_at
                    FROM notion_sync_status 
                    ORDER BY created_at DESC
                ''')
            
            sync_records = cursor.fetchall()
            
            if not sync_records:
                print("📝 Записи синхронизации с Notion не найдены")
                return
            
            if limit:
                print(f"📝 Статус синхронизации с Notion (последние {len(sync_records)}):")
            else:
                print(f"📝 Все {len(sync_records)} записей синхронизации с Notion:")
            print("=" * 140)
            print(f"{'ID':<3} {'Event ID':<15} {'Page ID':<15} {'Статус':<8} {'Последняя синхронизация':<20} {'Создано':<20}")
            print("=" * 140)
            
            for record in sync_records:
                page_id = record['page_id'][:12] + '...' if record['page_id'] and len(record['page_id']) > 15 else (record['page_id'] or 'N/A')
                last_sync = record['last_sync'][:19] if record['last_sync'] else 'N/A'
                created_time = record['created_at'][:19] if record['created_at'] else 'N/A'
                
                print(f"{record['id']:<3} {record['event_id']:<15} {page_id:<15} {record['sync_status']:<8} {last_sync:<20} {created_time:<20}")
            
            print("=" * 140)
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса синхронизации Notion: {e}")

    def show_folder_creation_status(self, limit: int = None):
        """Показывает статус создания папок."""
        try:
            cursor = self.conn.cursor()
            if limit:
                cursor.execute('''
                    SELECT 
                        id,
                        event_id,
                        folder_path,
                        account_type,
                        status,
                        created_at
                    FROM folder_creation_status 
                    ORDER BY created_at DESC 
                    LIMIT ?
                ''', (limit,))
            else:
                cursor.execute('''
                    SELECT 
                        id,
                        event_id,
                        folder_path,
                        account_type,
                        status,
                        created_at
                    FROM folder_creation_status 
                    ORDER BY created_at DESC
                ''')
            
            folders = cursor.fetchall()
            
            if not folders:
                print("📁 Записи создания папок не найдены")
                return
            
            if limit:
                print(f"📁 Статус создания папок (последние {len(folders)}):")
            else:
                print(f"📁 Все {len(folders)} записей создания папок:")
            print("=" * 120)
            print(f"{'ID':<3} {'Event ID':<15} {'Тип аккаунта':<8} {'Статус':<8} {'Создано':<20} {'Путь к папке':<50}")
            print("=" * 120)
            
            for folder in folders:
                folder_name = os.path.basename(folder['folder_path']) if folder['folder_path'] else 'N/A'
                created_time = folder['created_at'][:19] if folder['created_at'] else 'N/A'
                
                print(f"{folder['id']:<3} {folder['event_id']:<15} {folder['account_type']:<8} {folder['status']:<8} {created_time:<20} {folder_name:<50}")
            
            print("=" * 120)
            
        except Exception as e:
            print(f"❌ Ошибка получения статуса создания папок: {e}")


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
    
    # Команда для показа саммари
    summaries_parser = subparsers.add_parser('summaries', help='Показать обработанные саммари')
    summaries_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для показа статуса синхронизации с Notion
    notion_sync_parser = subparsers.add_parser('notion-sync', help='Показать статус синхронизации с Notion')
    notion_sync_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
    # Команда для показа статуса создания папок
    folders_parser = subparsers.add_parser('folders', help='Показать статус создания папок')
    folders_parser.add_argument('--limit', type=int, default=20, help='Количество записей')
    
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
        
        elif args.command == 'summaries':
            viewer.show_processed_summaries(args.limit)
        
        elif args.command == 'notion-sync':
            viewer.show_notion_sync_status(args.limit)
        
        elif args.command == 'folders':
            viewer.show_folder_creation_status(args.limit)
        
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
