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
                
                # Таблица для отслеживания синхронизации контента с Notion
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS notion_content_sync (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        sync_status TEXT DEFAULT 'pending',
                        synced_at TIMESTAMP,
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(event_id, content_type)
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
        Помечает транскрипцию как обработанную и обновляет Notion.
        
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
                
                # Пытаемся найти event_id по пути к файлу
                event_id = self._find_event_id_by_file_path(file_path)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_transcriptions 
                    (file_path, transcript_file, status, event_id, processed_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, transcript_file, status, event_id, datetime.now().isoformat()))
                conn.commit()
                
                # Если есть event_id и файл транскрипции, обновляем Notion
                if event_id and transcript_file and os.path.exists(transcript_file):
                    self._update_notion_with_transcription(event_id, transcript_file)
                
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
        Помечает саммари как обработанное и обновляет Notion.
        
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
                
                # Находим event_id для транскрипции
                cursor.execute('''
                    SELECT event_id FROM processed_transcriptions 
                    WHERE transcript_file = ?
                ''', (transcript_file,))
                
                result = cursor.fetchone()
                event_id = result[0] if result else None
                
                # Сохраняем саммари в БД
                cursor.execute('''
                    INSERT OR REPLACE INTO processed_summaries 
                    (transcript_file, summary_file, analysis_file, status, event_id, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (transcript_file, summary_file, analysis_file, status, event_id))
                
                conn.commit()
                
                # Если есть event_id и файлы саммари, обновляем Notion
                if event_id and summary_file and os.path.exists(summary_file):
                    self._update_notion_with_summary(event_id, summary_file, analysis_file)
                
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
    
    def _update_notion_with_summary(self, event_id: str, summary_file: str, analysis_file: str = ""):
        """
        Обновляет страницу Notion с саммари и анализом.
        
        Args:
            event_id: ID события
            summary_file: Путь к файлу саммари
            analysis_file: Путь к файлу анализа
        """
        try:
            # Получаем page_id для события
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT page_id FROM notion_sync_status 
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if not result or not result[0]:
                    self.logger.warning(f"⚠️ Page ID не найден для события {event_id}")
                    return
                
                page_id = result[0]
            
            # Читаем содержимое саммари
            if not os.path.exists(summary_file):
                self.logger.warning(f"⚠️ Файл саммари не найден: {summary_file}")
                return
            
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_content = f.read()
            
            # Читаем содержимое анализа (если есть)
            analysis_content = ""
            if analysis_file and os.path.exists(analysis_file):
                with open(analysis_file, 'r', encoding='utf-8') as f:
                    analysis_content = f.read()
            
            # Обновляем страницу Notion
            self._add_content_to_notion_page(page_id, summary_content, analysis_content)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления Notion с саммари: {e}")
    
    def _add_content_to_notion_page(self, page_id: str, summary_content: str, analysis_content: str = ""):
        """
        Добавляет контент в страницу Notion.
        
        Args:
            page_id: ID страницы в Notion
            summary_content: Содержимое саммари
            analysis_content: Содержимое анализа
        """
        try:
            import requests
            import os
            
            # Получаем токен из переменных окружения
            notion_token = os.getenv('NOTION_TOKEN')
            if not notion_token:
                self.logger.warning("⚠️ NOTION_TOKEN не найден в переменных окружения")
                return
            
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            # Формируем блоки для добавления
            blocks_to_add = []
            
            # Добавляем заголовок для саммари
            blocks_to_add.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📊 Саммари и анализ"
                            }
                        }
                    ]
                }
            })
            
            # Добавляем саммари
            blocks_to_add.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": summary_content
                            }
                        }
                    ]
                }
            })
            
            # Добавляем анализ (если есть)
            if analysis_content:
                blocks_to_add.append({
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "🔍 Детальный анализ"
                                }
                            }
                        ]
                    }
                })
                
                blocks_to_add.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": analysis_content
                                }
                            }
                        ]
                    }
                })
            
            # Добавляем контент в страницу
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            payload = {
                "children": blocks_to_add
            }
            
            response = requests.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            
            self.logger.info(f"✅ Страница Notion обновлена с саммари: {page_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления контента в Notion: {e}")
    
    def _find_event_id_by_file_path(self, file_path: str) -> str:
        """
        Находит event_id по пути к файлу.
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            event_id или None
        """
        try:
            import re
            
            # Извлекаем дату из пути
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path)
            if not date_match:
                return None
            
            date_str = date_match.group(1)
            
            # Извлекаем название события из пути
            path_parts = file_path.split('/')
            if len(path_parts) > 1:
                folder_name = path_parts[-2]  # Папка с событием
                
                # Очищаем название от даты и времени
                clean_folder_name = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}-\d{2}\s*', '', folder_name).strip()
                clean_folder_name = re.sub(r'[^\w\s]', '', clean_folder_name.lower()).strip()
                
                # Ищем событие в базе данных
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Ищем по дате
                    cursor.execute('''
                        SELECT event_id FROM processed_events 
                        WHERE event_start_time LIKE ?
                    ''', (f"{date_str}%",))
                    
                    results = cursor.fetchall()
                    if results:
                        # Если найдено несколько, выбираем первое
                        return results[0][0]
            
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска event_id по пути: {e}")
            return None
    
    def _update_notion_with_transcription(self, event_id: str, transcript_file: str):
        """
        Обновляет страницу Notion с транскрипцией.
        
        Args:
            event_id: ID события
            transcript_file: Путь к файлу транскрипции
        """
        try:
            # Получаем page_id для события
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT page_id FROM notion_sync_status 
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if not result or not result[0]:
                    self.logger.warning(f"⚠️ Page ID не найден для события {event_id}")
                    return
                
                page_id = result[0]
            
            # Читаем содержимое транскрипции
            if not os.path.exists(transcript_file):
                self.logger.warning(f"⚠️ Файл транскрипции не найден: {transcript_file}")
                return
            
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            
            # Обновляем страницу Notion
            self._add_transcription_to_notion_page(page_id, transcript_content)
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления Notion с транскрипцией: {e}")
    
    def _add_transcription_to_notion_page(self, page_id: str, transcript_content: str):
        """
        Добавляет транскрипцию в страницу Notion.
        
        Args:
            page_id: ID страницы в Notion
            transcript_content: Содержимое транскрипции
        """
        try:
            import requests
            import os
            
            # Получаем токен из переменных окружения
            notion_token = os.getenv('NOTION_TOKEN')
            if not notion_token:
                self.logger.warning("⚠️ NOTION_TOKEN не найден в переменных окружения")
                return
            
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            # Формируем блоки для добавления
            blocks_to_add = []
            
            # Добавляем заголовок для транскрипции
            blocks_to_add.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📝 Транскрипция встречи"
                            }
                        }
                    ]
                }
            })
            
            # Добавляем транскрипцию
            blocks_to_add.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": transcript_content
                            }
                        }
                    ]
                }
            })
            
            # Добавляем контент в страницу
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            payload = {
                "children": blocks_to_add
            }
            
            response = requests.patch(url, headers=headers, json=payload)
            response.raise_for_status()
            
            self.logger.info(f"✅ Страница Notion обновлена с транскрипцией: {page_id}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления транскрипции в Notion: {e}")

    def get_events_with_transcriptions_not_synced_to_notion(self) -> List[str]:
        """Получает список событий с транскрипциями, которые не синхронизированы в Notion."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем события с успешными транскрипциями, у которых есть Notion страницы
                cursor.execute('''
                    SELECT DISTINCT pt.event_id
                    FROM processed_transcriptions pt
                    JOIN notion_sync_status nss ON pt.event_id = nss.event_id
                    WHERE pt.status = 'success' 
                    AND nss.sync_status = 'success'
                    AND NOT EXISTS (
                        SELECT 1 FROM notion_content_sync ncs 
                        WHERE ncs.event_id = pt.event_id 
                        AND ncs.content_type = 'transcription'
                        AND ncs.sync_status = 'success'
                    )
                ''')
                
                events = [row[0] for row in cursor.fetchall()]
                self.logger.info(f"📝 Найдено {len(events)} событий с транскрипциями для синхронизации в Notion")
                return events
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения событий с транскрипциями: {e}")
            return []

    def get_events_with_summaries_not_synced_to_notion(self) -> List[str]:
        """Получает список событий с саммари, которые не синхронизированы в Notion."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем события с успешными саммари, у которых есть Notion страницы
                cursor.execute('''
                    SELECT DISTINCT ps.event_id
                    FROM processed_summaries ps
                    JOIN notion_sync_status nss ON ps.event_id = nss.event_id
                    WHERE ps.status = 'success' 
                    AND nss.sync_status = 'success'
                    AND NOT EXISTS (
                        SELECT 1 FROM notion_content_sync ncs 
                        WHERE ncs.event_id = ps.event_id 
                        AND ncs.content_type = 'summary'
                        AND ncs.sync_status = 'success'
                    )
                ''')
                
                events = [row[0] for row in cursor.fetchall()]
                self.logger.info(f"📝 Найдено {len(events)} событий с саммари для синхронизации в Notion")
                return events
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения событий с саммари: {e}")
            return []

    def get_transcription_data(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные транскрипции для события."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT status, file_path, processed_at, transcript_file
                    FROM processed_transcriptions
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'status': result[0],
                        'file_path': result[1],
                        'created_at': result[2],
                        'transcript_file': result[3]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения данных транскрипции для {event_id}: {e}")
            return None

    def get_summary_data(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные саммари для события."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT status, transcript_file, summary_file, analysis_file, created_at
                    FROM processed_summaries
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'status': result[0],
                        'transcript_file': result[1],
                        'summary_file': result[2],
                        'analysis_file': result[3],
                        'created_at': result[4]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения данных саммари для {event_id}: {e}")
            return None

    def get_event_data(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получает данные события."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT event_title, event_start_time, event_end_time, 
                           attendees, meeting_link, calendar_type
                    FROM processed_events
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'event_id': event_id,
                        'event_title': result[0],
                        'event_start_time': result[1],
                        'event_end_time': result[2],
                        'attendees': result[3],
                        'meeting_link': result[4],
                        'calendar_type': result[5]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения данных события {event_id}: {e}")
            return None

    def get_notion_sync_status(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Получает статус синхронизации с Notion для события."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT page_id, sync_status, created_at
                    FROM notion_sync_status
                    WHERE event_id = ?
                ''', (event_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'page_id': result[0],
                        'sync_status': result[1],
                        'created_at': result[2]
                    }
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения статуса Notion для {event_id}: {e}")
            return None

    def record_content_sync_status(self, event_id: str, content_type: str, status: str, error_message: str = None):
        """Записывает статус синхронизации контента в БД."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Вставляем или обновляем запись
                cursor.execute('''
                    INSERT OR REPLACE INTO notion_content_sync 
                    (event_id, content_type, sync_status, synced_at, error_message, created_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    event_id,
                    content_type,
                    status,
                    datetime.now().isoformat() if status == 'success' else None,
                    error_message
                ))
                
                conn.commit()
                self.logger.info(f"✅ Статус синхронизации записан: {event_id} - {content_type} - {status}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи статуса синхронизации: {e}")
