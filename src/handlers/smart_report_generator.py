#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор умных отчетов для Telegram
Группирует информацию по папкам встреч и показывает только изменения
"""

import os
import time
from typing import Dict, Any, List, Optional
from datetime import datetime


class SmartReportGenerator:
    """Генератор умных отчетов для Telegram."""
    
    def __init__(self, logger=None):
        """
        Инициализация генератора отчетов.
        
        Args:
            logger: Логгер
        """
        self.logger = logger
        self.last_report_time = None
        self.last_errors = set()
    
    def generate_smart_report(self, current_state: Dict[str, Any], 
                            previous_state: Optional[Dict[str, Any]] = None,
                            execution_time: float = 0) -> Optional[str]:
        """
        Генерирует умный отчет только при наличии изменений.
        
        Args:
            current_state: Текущее состояние системы
            previous_state: Предыдущее состояние системы
            execution_time: Время выполнения цикла
            
        Returns:
            Текст отчета или None если изменений нет
        """
        try:
            # Проверяем, есть ли реальные изменения
            if not self._has_real_changes(current_state, previous_state):
                if self.logger:
                    self.logger.debug("🔍 Изменений нет, отчет не генерируется")
                return None
            
            # Генерируем отчет
            report = self._build_smart_report(current_state, previous_state, execution_time)
            
            # Обновляем время последнего отчета
            self.last_report_time = datetime.now()
            
            return report
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка генерации умного отчета: {e}")
            return None
    
    def _has_real_changes(self, current_state: Dict[str, Any], 
                         previous_state: Optional[Dict[str, Any]]) -> bool:
        """
        Проверяет, есть ли реальные изменения в системе.
        
        Args:
            current_state: Текущее состояние
            previous_state: Предыдущее состояние
            
        Returns:
            True если есть изменения, False иначе
        """
        try:
            self.logger.info(f"🔍 SmartReportGenerator._has_real_changes: previous_state={bool(previous_state)}")
            if not previous_state:
                # Если предыдущего состояния нет, проверяем текущие метрики
                return self._has_current_activity(current_state)
            
            # Сравниваем ключевые метрики
            current_metrics = self._extract_metrics(current_state)
            previous_metrics = self._extract_metrics(previous_state)
            
            self.logger.info(f"🔍 SmartReportGenerator: current_metrics={current_metrics}")
            self.logger.info(f"🔍 SmartReportGenerator: previous_metrics={previous_metrics}")
            
            # Проверяем изменения в метриках
            for key in current_metrics:
                if current_metrics[key] != previous_metrics[key]:
                    if self.logger:
                        self.logger.info(f"🔍 Обнаружены изменения в {key}: {previous_metrics[key]} -> {current_metrics[key]}")
                    return True
            
            # Убираем эту проверку - она всегда возвращала True при любой активности
            # Теперь отчет будет генерироваться только при реальных изменениях в метриках
            # или при появлении новых ошибок
            
            # Проверяем новые ошибки
            current_errors = self._extract_errors(current_state)
            if current_errors - self.last_errors:
                if self.logger:
                    self.logger.info(f"🔍 Обнаружены новые ошибки: {current_errors - self.last_errors}")
                return True
            
            return False
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Ошибка проверки изменений: {e}")
            return True  # В случае ошибки считаем что есть изменения
    
    def _has_current_activity(self, current_state: Dict[str, Any]) -> bool:
        """
        Проверяет, есть ли активность в текущем состоянии.
        
        Args:
            current_state: Текущее состояние
            
        Returns:
            True если есть активность, False иначе
        """
        try:
            # Проверяем ключевые метрики
            personal_processed = current_state.get('personal_events', {}).get('processed', 0)
            work_processed = current_state.get('work_events', {}).get('processed', 0)
            media_processed = current_state.get('media_processed', {}).get('count', 0)
            transcriptions = current_state.get('transcriptions', {}).get('count', 0)
            notion_synced = current_state.get('notion_synced', {}).get('count', 0)
            errors_count = current_state.get('errors_count', 0)
            
            # Проверяем реальную активность (не просто "processed: 1")
            # Убираем transcriptions > 0, так как это может быть повторная обработка
            has_real_activity = (
                media_processed > 0 or 
                notion_synced > 0 or 
                errors_count > 0
            )
            
            self.logger.info(f"🔍 SmartReportGenerator._has_current_activity: media={media_processed}, transcriptions={transcriptions}, notion={notion_synced}, errors={errors_count}, has_real_activity={has_real_activity}")
            
            if self.logger:
                self.logger.debug(f"🔍 Проверка активности: media={media_processed}, transcriptions={transcriptions}, notion={notion_synced}, errors={errors_count}, real={has_real_activity}")
            
            return has_real_activity
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"⚠️ Ошибка проверки активности: {e}")
            return True
    
    def _extract_metrics(self, state: Dict[str, Any]) -> Dict[str, int]:
        """
        Извлекает ключевые метрики из состояния.
        
        Args:
            state: Состояние системы
            
        Returns:
            Словарь метрик
        """
        try:
            return {
                'personal_events': state.get('personal_events', {}).get('processed', 0),
                'work_events': state.get('work_events', {}).get('processed', 0),
                'media_processed': state.get('media_processed', {}).get('count', 0),
                'transcriptions': state.get('transcriptions', {}).get('count', 0),
                'notion_synced': state.get('notion_synced', {}).get('count', 0),
                'errors_count': state.get('errors_count', 0)
            }
        except Exception:
            return {}
    
    def _extract_errors(self, state: Dict[str, Any]) -> set:
        """
        Извлекает ошибки из состояния.
        
        Args:
            state: Состояние системы
            
        Returns:
            Множество ошибок
        """
        try:
            errors = set()
            
            # Ошибки в аккаунтах
            personal_status = state.get('personal_events', {}).get('status', '')
            work_status = state.get('work_events', {}).get('status', '')
            
            if personal_status == 'error':
                errors.add(f"Личный аккаунт: {state.get('personal_events', {}).get('message', 'Ошибка')}")
            
            if work_status == 'error':
                errors.add(f"Рабочий аккаунт: {state.get('work_events', {}).get('message', 'Ошибка')}")
            
            # Ошибки в медиа
            media_status = state.get('media_processed', {}).get('status', '')
            if media_status == 'error':
                errors.add(f"Медиа: {state.get('media_processed', {}).get('message', 'Ошибка')}")
            
            # Ошибки в транскрипциях
            transcription_status = state.get('transcriptions', {}).get('status', '')
            if transcription_status == 'error':
                errors.add(f"Транскрипции: {state.get('transcriptions', {}).get('message', 'Ошибка')}")
            
            # Ошибки в Notion
            notion_status = state.get('notion_synced', {}).get('status', '')
            if notion_status == 'error':
                errors.add(f"Notion: {state.get('notion_synced', {}).get('message', 'Ошибка')}")
            
            return errors
            
        except Exception:
            return set()
    
    def _build_smart_report(self, current_state: Dict[str, Any], 
                           previous_state: Optional[Dict[str, Any]], 
                           execution_time: float) -> str:
        """
        Строит умный отчет с группировкой по папкам встреч.
        
        Args:
            current_state: Текущее состояние
            previous_state: Предыдущее состояние
            execution_time: Время выполнения
            
        Returns:
            Текст отчета
        """
        try:
            report = "🤖 <b>Отчет системы автоматизации встреч</b>\n\n"
            
            # Время выполнения
            current_time = datetime.now().strftime("%H:%M:%S")
            report += f"⏰ Завершено {current_time}\n\n"
            
            # Группируем изменения по папкам встреч
            meeting_changes = self._group_changes_by_meetings(current_state, previous_state)
            
            if meeting_changes:
                report += "📊 <b>Изменения по встречам:</b>\n\n"
                
                for meeting_folder, changes in meeting_changes.items():
                    meeting_name = os.path.basename(meeting_folder)
                    account_icon = "👤" if "personal" in meeting_folder else "🏢"
                    
                    report += f"{account_icon} <b>{meeting_name}</b>\n"
                    
                    for change in changes:
                        report += f"    {change}\n"
                    
                    report += "\n"
                
                # Список обработанных файлов
                processed_files = self._get_processed_files(current_state)
                if processed_files:
                    report += "📁 <b>Обработаны файлы:</b>\n"
                    for file_info in processed_files:
                        report += f"• {file_info}\n"
                    report += "\n"
            
            # Ошибки и замечания
            current_errors = self._extract_errors(current_state)
            if current_errors:
                report += "⚠️ <b>Ошибки и замечания:</b>\n"
                for error in current_errors:
                    report += f"• {error}\n"
                report += "\n"
            else:
                report += "🎯 <b>🟢 ошибок и замечаний нет</b>\n\n"
            
            # Время выполнения
            if execution_time > 0:
                report += f"⏱️ <b>время выполнения</b> {execution_time:.2f} секунд\n"
            
            return report
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка построения отчета: {e}")
            return f"❌ Ошибка генерации отчета: {e}"
    
    def _group_changes_by_meetings(self, current_state: Dict[str, Any], 
                                  previous_state: Optional[Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Группирует изменения по папкам встреч.
        
        Args:
            current_state: Текущее состояние
            previous_state: Предыдущее состояние
            
        Returns:
            Словарь изменений по папкам
        """
        try:
            meeting_changes = {}
            
            # Медиа файлы
            media_info = current_state.get('media_processed', {})
            if media_info.get('count', 0) > 0:
                for folder_info in media_info.get('folders', []):
                    folder_path = folder_info.get('folder', '')
                    if folder_path:
                        if folder_path not in meeting_changes:
                            meeting_changes[folder_path] = []
                        
                        processed_count = folder_info.get('processed', 0)
                        if processed_count > 0:
                            meeting_changes[folder_path].append("🎬 сжато видео")
                            meeting_changes[folder_path].append("🎙️ выделено аудио")
            
            # Транскрипции
            transcription_info = current_state.get('transcriptions', {})
            if transcription_info.get('count', 0) > 0:
                for folder_info in transcription_info.get('folders', []):
                    folder_path = folder_info.get('folder', '')
                    if folder_path:
                        if folder_path not in meeting_changes:
                            meeting_changes[folder_path] = []
                        
                        processed_count = folder_info.get('processed', 0)
                        if processed_count > 0:
                            meeting_changes[folder_path].append("📝 транскрибировано аудио")
            
            # Саммари
            summary_info = current_state.get('summaries', {})
            if summary_info.get('count', 0) > 0:
                for folder_info in summary_info.get('folders', []):
                    folder_path = folder_info.get('folder', '')
                    if folder_path:
                        if folder_path not in meeting_changes:
                            meeting_changes[folder_path] = []
                        
                        processed_count = folder_info.get('processed', 0)
                        if processed_count > 0:
                            meeting_changes[folder_path].append("🧑🏻‍💻 подготовлено саммари")
                            meeting_changes[folder_path].append("👩‍⚕️ готов анализ")
            
            # Notion синхронизация
            notion_info = current_state.get('notion_synced', {})
            if notion_info.get('count', 0) > 0:
                for folder_info in notion_info.get('folders', []):
                    folder_path = folder_info.get('folder', '')
                    if folder_path:
                        if folder_path not in meeting_changes:
                            meeting_changes[folder_path] = []
                        
                        meeting_changes[folder_path].append("📙 записано в notion")
            
            # Добавляем статус завершения для каждой папки
            for folder_path in meeting_changes:
                meeting_changes[folder_path].append("✅ Обработка завершена")
            
            return meeting_changes
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка группировки изменений: {e}")
            return {}
    
    def _get_processed_files(self, current_state: Dict[str, Any]) -> List[str]:
        """
        Получает список обработанных файлов.
        
        Args:
            current_state: Текущее состояние
            
        Returns:
            Список файлов
        """
        try:
            files = []
            
            # Медиа файлы
            media_info = current_state.get('media_processed', {})
            if media_info.get('count', 0) > 0:
                for folder_info in media_info.get('folders', []):
                    for file_info in folder_info.get('files', []):
                        if isinstance(file_info, dict):
                            file_name = file_info.get('file', '')
                            status = file_info.get('status', '')
                            if file_name and status == 'success':
                                files.append(f"{file_name} (медиа)")
                        else:
                            files.append(f"{file_info} (медиа)")
            
            # Транскрипции
            transcription_info = current_state.get('transcriptions', {})
            if transcription_info.get('count', 0) > 0:
                for folder_info in transcription_info.get('folders', []):
                    for file_info in folder_info.get('files', []):
                        if isinstance(file_info, dict):
                            file_name = file_info.get('file', '')
                            status = file_info.get('status', '')
                            if file_name and status == 'success':
                                files.append(f"{file_name} (транскрипция)")
                        else:
                            files.append(f"{file_info} (транскрипция)")
            
            return files[:10]  # Ограничиваем количество файлов
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка получения файлов: {e}")
            return []
