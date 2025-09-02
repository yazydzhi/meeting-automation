#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер состояния системы с использованием SQLite базы данных.
Отслеживает изменения и определяет, что нужно обработать.
"""

import sqlite3
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path


class StateManager:
    """Менеджер состояния системы с SQLite."""
    
    def __init__(self, db_path: str = "data/system_state.db", logger=None):
        """
        Инициализация менеджера состояния.
        
        Args:
            db_path: Путь к базе данных SQLite
            logger: Логгер
        """
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)
        
        # Создаем директорию для базы данных
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Инициализируем базу данных
        self._init_database()
    
    def _init_database(self):
        """Инициализация базы данных и создание таблиц."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица для хранения состояния системы
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_state (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        cycle_id INTEGER NOT NULL,
                        personal_events_processed INTEGER DEFAULT 0,
                        work_events_processed INTEGER DEFAULT 0,
                        media_processed INTEGER DEFAULT 0,
                        transcriptions_processed INTEGER DEFAULT 0,
                        notion_synced INTEGER DEFAULT 0,
                        errors_count INTEGER DEFAULT 0,
                        personal_status TEXT DEFAULT 'success',
                        work_status TEXT DEFAULT 'success',
                        media_status TEXT DEFAULT 'success',
                        transcription_status TEXT DEFAULT 'success',
                        notion_status TEXT DEFAULT 'success',
                        execution_time REAL DEFAULT 0.0,
                        raw_state TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Таблица для отслеживания обработанных событий календаря
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL,
                        account_type TEXT NOT NULL,
                        event_title TEXT,
                        event_start_time TEXT,
                        event_end_time TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(event_id, account_type)
                    )
                ''')
                
                # Таблица для отслеживания обработанных медиа файлов
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_media (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL UNIQUE,
                        file_hash TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'success'
                    )
                ''')
                
                # Таблица для отслеживания обработанных транскрипций
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS processed_transcriptions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        file_path TEXT NOT NULL UNIQUE,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'success'
                    )
                ''')
                
                # Таблица для отслеживания синхронизации с Notion
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notion_sync (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        page_id TEXT NOT NULL UNIQUE,
                        event_id TEXT,
                        last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'success'
                    )
                ''')
                
                # Создаем индексы для быстрого поиска
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_events_event_id ON processed_events(event_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_processed_events_account ON processed_events(account_type)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_state_timestamp ON system_state(timestamp)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_state_cycle ON system_state(cycle_id)')
                
                conn.commit()
                self.logger.info(f"✅ База данных инициализирована: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            raise
    
    def save_system_state(self, state: Dict[str, Any], cycle_id: int) -> bool:
        """
        Сохраняет состояние системы в базу данных.
        
        Args:
            state: Состояние системы
            cycle_id: ID цикла обработки
            
        Returns:
            True если сохранение успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Извлекаем метрики из состояния
                personal_events = state.get('personal_events', {})
                work_events = state.get('work_events', {})
                media_processed = state.get('media_processed', {})
                transcriptions = state.get('transcriptions', {})
                notion_synced = state.get('notion_synced', {})
                
                cursor.execute('''
                    INSERT INTO system_state (
                        timestamp, cycle_id, personal_events_processed, work_events_processed,
                        media_processed, transcriptions_processed, notion_synced, errors_count,
                        personal_status, work_status, media_status, transcription_status, notion_status,
                        execution_time, raw_state
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    cycle_id,
                    personal_events.get('processed', 0),
                    work_events.get('processed', 0),
                    media_processed.get('count', 0),
                    transcriptions.get('count', 0),
                    notion_synced.get('count', 0),
                    state.get('errors_count', 0),
                    personal_events.get('status', 'success'),
                    work_events.get('status', 'success'),
                    media_processed.get('status', 'success'),
                    transcriptions.get('status', 'success'),
                    notion_synced.get('status', 'success'),
                    state.get('execution_time', 0.0),
                    json.dumps(state, ensure_ascii=False)
                ))
                
                conn.commit()
                self.logger.debug(f"✅ Состояние системы сохранено (цикл {cycle_id})")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения состояния системы: {e}")
            return False
    
    def get_last_state(self) -> Optional[Dict[str, Any]]:
        """
        Получает последнее сохраненное состояние системы.
        
        Returns:
            Последнее состояние или None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT raw_state FROM system_state 
                    ORDER BY created_at DESC LIMIT 1
                ''')
                
                result = cursor.fetchone()
                if result:
                    return json.loads(result[0])
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения последнего состояния: {e}")
            return None
    
    def has_changes(self, current_state: Dict[str, Any]) -> bool:
        """
        Проверяет, есть ли изменения по сравнению с последним состоянием.
        
        Args:
            current_state: Текущее состояние
            
        Returns:
            True если есть изменения, False иначе
        """
        try:
            last_state = self.get_last_state()
            if not last_state:
                # Если нет предыдущего состояния, проверяем есть ли активность
                return self._has_current_activity(current_state)
            
            # Сравниваем ключевые метрики
            current_metrics = self._extract_metrics(current_state)
            last_metrics = self._extract_metrics(last_state)
            
            self.logger.debug(f"🔍 Сравнение метрик: current={current_metrics}, last={last_metrics}")
            
            # Проверяем изменения в метриках (только увеличение)
            for key in current_metrics:
                if current_metrics[key] > last_metrics[key]:
                    self.logger.info(f"🔍 Обнаружены изменения в {key}: {last_metrics[key]} -> {current_metrics[key]}")
                    return True
            
            # Проверяем новые ошибки
            if current_metrics['errors_count'] > 0 and last_metrics['errors_count'] == 0:
                self.logger.info(f"🔍 Обнаружены новые ошибки: {last_metrics['errors_count']} -> {current_metrics['errors_count']}")
                return True
            
            # Проверяем изменения в статусах (только ошибки)
            current_statuses = self._extract_statuses(current_state)
            last_statuses = self._extract_statuses(last_state)
            
            for key in current_statuses:
                if (current_statuses[key] == 'error' and last_statuses[key] != 'error') or \
                   (last_statuses[key] == 'error' and current_statuses[key] != 'error'):
                    self.logger.info(f"🔍 Обнаружены изменения в статусе {key}: {last_statuses[key]} -> {current_statuses[key]}")
                    return True
            
            self.logger.debug("🔍 Изменений не обнаружено")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки изменений: {e}")
            return True  # В случае ошибки считаем что есть изменения
    
    def _extract_metrics(self, state: Dict[str, Any]) -> Dict[str, int]:
        """Извлекает ключевые метрики из состояния."""
        return {
            'personal_events': state.get('personal_events', {}).get('processed', 0),
            'work_events': state.get('work_events', {}).get('processed', 0),
            'media_processed': state.get('media_processed', {}).get('count', 0),
            'transcriptions': state.get('transcriptions', {}).get('count', 0),
            'notion_synced': state.get('notion_synced', {}).get('count', 0),
            'errors_count': state.get('errors_count', 0)
        }
    
    def _extract_statuses(self, state: Dict[str, Any]) -> Dict[str, str]:
        """Извлекает статусы из состояния."""
        return {
            'personal_status': state.get('personal_events', {}).get('status', 'success'),
            'work_status': state.get('work_events', {}).get('status', 'success'),
            'media_status': state.get('media_processed', {}).get('status', 'success'),
            'transcription_status': state.get('transcriptions', {}).get('status', 'success'),
            'notion_status': state.get('notion_synced', {}).get('status', 'success')
        }
    
    def _has_current_activity(self, state: Dict[str, Any]) -> bool:
        """Проверяет, есть ли активность в текущем состоянии."""
        metrics = self._extract_metrics(state)
        return any(metrics[key] > 0 for key in metrics)
    
    def mark_event_processed(self, event_id: str, account_type: str, event_title: str = "", 
                           event_start_time: str = "", event_end_time: str = "", 
                           attendees: str = "", meeting_link: str = "", calendar_type: str = "") -> bool:
        """
        Помечает событие календаря как обработанное.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта
            event_title: Название события
            event_start_time: Время начала события
            event_end_time: Время окончания события
            attendees: Участники встречи (JSON строка или список через запятую)
            meeting_link: Ссылка на встречу
            calendar_type: Тип календаря (google_calendar, ical_calendar)
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_events 
                    (event_id, account_type, event_title, event_start_time, event_end_time, 
                     attendees, meeting_link, calendar_type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (event_id, account_type, event_title, event_start_time, event_end_time,
                      attendees, meeting_link, calendar_type))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки события как обработанного: {e}")
            return False
    
    def is_event_processed(self, event_id: str, account_type: str) -> bool:
        """
        Проверяет, было ли событие уже обработано.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта
            
        Returns:
            True если событие уже обработано, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 1 FROM processed_events 
                    WHERE event_id = ? AND account_type = ?
                ''', (event_id, account_type))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса события: {e}")
            return False
    
    def mark_media_processed(self, file_path: str, file_hash: str = "", status: str = "success") -> bool:
        """
        Помечает медиа файл как обработанный.
        
        Args:
            file_path: Путь к файлу
            file_hash: Хеш файла
            status: Статус обработки
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_media (file_path, file_hash, status)
                    VALUES (?, ?, ?)
                ''', (file_path, file_hash, status))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки медиа файла как обработанного: {e}")
            return False
    
    def is_media_processed(self, file_path: str) -> bool:
        """
        Проверяет, был ли медиа файл уже обработан.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            True если файл уже обработан, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT 1 FROM processed_media 
                    WHERE file_path = ?
                ''', (file_path,))
                
                return cursor.fetchone() is not None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса медиа файла: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику из базы данных.
        
        Returns:
            Словарь со статистикой
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Общая статистика
                cursor.execute('SELECT COUNT(*) FROM system_state')
                total_cycles = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM processed_events')
                total_events = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM processed_media')
                total_media = cursor.fetchone()[0]
                
                cursor.execute('SELECT COUNT(*) FROM processed_transcriptions')
                total_transcriptions = cursor.fetchone()[0]
                
                # Последний цикл
                cursor.execute('''
                    SELECT cycle_id, timestamp, personal_events_processed, work_events_processed,
                           media_processed, transcriptions_processed, notion_synced, errors_count
                    FROM system_state 
                    ORDER BY created_at DESC LIMIT 1
                ''')
                
                last_cycle = cursor.fetchone()
                
                return {
                    'total_cycles': total_cycles,
                    'total_events': total_events,
                    'total_media': total_media,
                    'total_transcriptions': total_transcriptions,
                    'last_cycle': {
                        'cycle_id': last_cycle[0] if last_cycle else 0,
                        'timestamp': last_cycle[1] if last_cycle else None,
                        'personal_events_processed': last_cycle[2] if last_cycle else 0,
                        'work_events_processed': last_cycle[3] if last_cycle else 0,
                        'media_processed': last_cycle[4] if last_cycle else 0,
                        'transcriptions_processed': last_cycle[5] if last_cycle else 0,
                        'notion_synced': last_cycle[6] if last_cycle else 0,
                        'errors_count': last_cycle[7] if last_cycle else 0
                    } if last_cycle else None
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статистики: {e}")
            return {}
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Очищает старые данные из базы данных.
        
        Args:
            days_to_keep: Количество дней для хранения данных
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Удаляем старые состояния системы
                cursor.execute('''
                    DELETE FROM system_state 
                    WHERE created_at < datetime('now', '-{} days')
                '''.format(days_to_keep))
                
                deleted_states = cursor.rowcount
                
                # Удаляем старые записи о событиях
                cursor.execute('''
                    DELETE FROM processed_events 
                    WHERE processed_at < datetime('now', '-{} days')
                '''.format(days_to_keep))
                
                deleted_events = cursor.rowcount
                
                conn.commit()
                
                self.logger.info(f"🧹 Очистка базы данных: удалено {deleted_states} состояний, {deleted_events} событий")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка очистки базы данных: {e}")
    
    def mark_transcription_processed(self, file_path: str, transcript_file: str, status: str = "success") -> bool:
        """
        Помечает транскрипцию как обработанную.
        
        Args:
            file_path: Путь к исходному аудио файлу
            transcript_file: Путь к файлу транскрипции
            status: Статус обработки
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_transcriptions 
                    (file_path, transcript_file, status, processed_at)
                    VALUES (?, ?, ?, ?)
                ''', (file_path, transcript_file, status, datetime.now().isoformat()))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки транскрипции как обработанной: {e}")
            return False
    
    def is_transcription_processed(self, file_path: str) -> bool:
        """
        Проверяет, была ли транскрипция уже обработана.
        
        Args:
            file_path: Путь к аудио файлу
            
        Returns:
            True если уже обработана, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_transcriptions 
                    WHERE file_path = ? AND status = 'success'
                ''', (file_path,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса транскрипции: {e}")
            return False
    
    def mark_media_processed(self, file_path: str, compressed_video: str = "", compressed_audio: str = "", status: str = "success") -> bool:
        """
        Помечает медиа файл как обработанный.
        
        Args:
            file_path: Путь к исходному медиа файлу
            compressed_video: Путь к сжатому видео файлу
            compressed_audio: Путь к сжатому аудио файлу
            status: Статус обработки
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_media 
                    (file_path, compressed_video, compressed_audio, status, processed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, compressed_video, compressed_audio, status, datetime.now().isoformat()))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки медиа файла как обработанного: {e}")
            return False
    
    def is_media_processed(self, file_path: str) -> bool:
        """
        Проверяет, был ли медиа файл уже обработан.
        
        Args:
            file_path: Путь к медиа файлу
            
        Returns:
            True если уже обработан, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_media 
                    WHERE file_path = ? AND status = 'success'
                ''', (file_path,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса медиа файла: {e}")
            return False

    # ===== МЕТОДЫ ДЛЯ ОТСЛЕЖИВАНИЯ САММАРИ =====
    
    def mark_summary_processed(self, transcript_file: str, summary_file: str = "", analysis_file: str = "", status: str = "success") -> bool:
        """
        Помечает саммари как обработанное.
        
        Args:
            transcript_file: Путь к файлу транскрипции
            summary_file: Путь к файлу саммари
            analysis_file: Путь к файлу анализа
            status: Статус обработки
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_summaries 
                    (transcript_file, summary_file, analysis_file, status, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (transcript_file, summary_file, analysis_file, status))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки саммари как обработанного: {e}")
            return False
    
    def is_summary_processed(self, transcript_file: str) -> bool:
        """
        Проверяет, было ли саммари уже обработано.
        
        Args:
            transcript_file: Путь к файлу транскрипции
            
        Returns:
            True если уже обработано, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_summaries 
                    WHERE transcript_file = ? AND status = 'success'
                ''', (transcript_file,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса саммари: {e}")
            return False

    # ===== МЕТОДЫ ДЛЯ ОТСЛЕЖИВАНИЯ СИНХРОНИЗАЦИИ NOTION =====
    
    def mark_notion_synced(self, event_id: str, page_id: str = "", page_url: str = "", sync_status: str = "success") -> bool:
        """
        Помечает событие как синхронизированное с Notion.
        
        Args:
            event_id: ID события
            page_id: ID страницы в Notion
            page_url: URL страницы в Notion
            sync_status: Статус синхронизации
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO notion_sync_status 
                    (event_id, page_id, page_url, sync_status, last_sync, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (event_id, page_id, page_url, sync_status))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки синхронизации Notion: {e}")
            return False
    
    def is_notion_synced(self, event_id: str) -> bool:
        """
        Проверяет, было ли событие синхронизировано с Notion.
        
        Args:
            event_id: ID события
            
        Returns:
            True если уже синхронизировано, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM notion_sync_status 
                    WHERE event_id = ? AND sync_status = 'success'
                ''', (event_id,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса синхронизации Notion: {e}")
            return False

    # ===== МЕТОДЫ ДЛЯ ОТСЛЕЖИВАНИЯ СОЗДАНИЯ ПАПОК =====
    
    def mark_folder_created(self, event_id: str, folder_path: str, account_type: str, status: str = "success") -> bool:
        """
        Помечает папку как созданную.
        
        Args:
            event_id: ID события
            folder_path: Путь к папке
            account_type: Тип аккаунта (personal/work)
            status: Статус создания
            
        Returns:
            True если успешно, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO folder_creation_status 
                    (event_id, folder_path, account_type, status, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (event_id, folder_path, account_type, status))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки создания папки: {e}")
            return False
    
    def is_folder_created(self, event_id: str, account_type: str) -> bool:
        """
        Проверяет, была ли папка уже создана.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта (personal/work)
            
        Returns:
            True если уже создана, False иначе
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT COUNT(*) FROM folder_creation_status 
                    WHERE event_id = ? AND account_type = ? AND status = 'success'
                ''', (event_id, account_type))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса создания папки: {e}")
            return False
