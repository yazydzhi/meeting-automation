#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для работы с метриками
"""

from typing import Dict, Any, List
from .base_handler import BaseHandler


class MetricsHandler(BaseHandler):
    """Базовый класс для работы с метриками."""
    
    def __init__(self, config_manager, logger=None):
        """
        Инициализация обработчика метрик.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        
        # Константы для ключей метрик
        self.METRIC_KEYS = [
            'personal_events',
            'work_events', 
            'media_processed',
            'transcriptions',
            'notion_synced',
            'errors_count'
        ]
        
        # Константы для ключей статусов
        self.STATUS_KEYS = [
            'personal_status',
            'work_status',
            'media_status',
            'transcription_status',
            'notion_status'
        ]
    
    def has_changes(self, current_state: Dict[str, Any], previous_state: Dict[str, Any]) -> bool:
        """
        Проверка наличия изменений в состоянии системы.
        
        Args:
            current_state: Текущее состояние
            previous_state: Предыдущее состояние
            
        Returns:
            True если есть изменения, False если изменений нет
        """
        try:
            self.logger.info(f"🔍 Проверка изменений: previous_state={bool(previous_state)}")
            
            if not previous_state:
                # Если предыдущее состояние отсутствует, проверяем есть ли реальные изменения
                # в текущем состоянии (обработанные события, ошибки, etc.)
                return self._has_real_changes(current_state)
            
            # Проверяем изменения в ключевых метриках
            current_metrics = self._extract_metrics(current_state)
            previous_metrics = self._extract_metrics(previous_state)
            
            self.logger.info(f"🔍 Сравнение метрик: current={current_metrics}, previous={previous_metrics}")
            
            # Проверяем изменения в метриках
            for key in self.METRIC_KEYS:
                if current_metrics[key] != previous_metrics[key]:
                    self.logger.info(f"🔍 Обнаружены изменения в {key}: {previous_metrics[key]} -> {current_metrics[key]}")
                    return True
            
            # Проверяем изменения в статусах
            current_statuses = self._extract_statuses(current_state)
            previous_statuses = self._extract_statuses(previous_state)
            
            for key in self.STATUS_KEYS:
                if current_statuses[key] != previous_statuses[key]:
                    self.logger.info(f"🔍 Обнаружены изменения в {key}: {previous_statuses[key]} -> {current_statuses[key]}")
                    return True
            
            self.logger.info("🔍 Изменений не обнаружено")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки изменений: {e}")
            # В случае ошибки считаем, что есть изменения (безопасный подход)
            return True
    
    def _has_real_changes(self, current_state: Dict[str, Any]) -> bool:
        """
        Проверяет наличие реальных изменений в текущем состоянии.
        
        Args:
            current_state: Текущее состояние
            
        Returns:
            True если есть реальные изменения, False иначе
        """
        try:
            personal_processed = current_state.get('personal_events', {}).get('processed', 0)
            work_processed = current_state.get('work_events', {}).get('processed', 0)
            media_processed = current_state.get('media_processed', {}).get('count', 0)
            transcriptions = current_state.get('transcriptions', {}).get('count', 0)
            notion_synced = current_state.get('notion_synced', {}).get('count', 0)
            errors_count = current_state.get('errors_count', 0)
            
            self.logger.info(f"🔍 Метрики без предыдущего состояния: personal={personal_processed}, work={work_processed}, media={media_processed}, transcriptions={transcriptions}, notion={notion_synced}, errors={errors_count}")
            
            # Если есть реальные изменения, считаем что есть изменения
            if (personal_processed > 0 or work_processed > 0 or 
                media_processed > 0 or transcriptions > 0 or 
                notion_synced > 0 or errors_count > 0):
                self.logger.info("🔍 Предыдущее состояние отсутствует, но есть реальные изменения")
                return True
            else:
                self.logger.info("🔍 Предыдущее состояние отсутствует, реальных изменений нет")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки реальных изменений: {e}")
            return False
    
    def _extract_metrics(self, state: Dict[str, Any]) -> Dict[str, int]:
        """
        Извлекает метрики из состояния.
        
        Args:
            state: Состояние системы
            
        Returns:
            Словарь с метриками
        """
        try:
            metrics = {}
            for key in self.METRIC_KEYS:
                if key == 'errors_count':
                    metrics[key] = state.get(key, 0)
                else:
                    metrics[key] = state.get(key, {}).get('processed', 0) if key in ['personal_events', 'work_events'] else state.get(key, {}).get('count', 0)
            return metrics
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения метрик: {e}")
            return {key: 0 for key in self.METRIC_KEYS}
    
    def _extract_statuses(self, state: Dict[str, Any]) -> Dict[str, str]:
        """
        Извлекает статусы из состояния.
        
        Args:
            state: Состояние системы
            
        Returns:
            Словарь со статусами
        """
        try:
            statuses = {}
            for key in self.STATUS_KEYS:
                if key == 'personal_status':
                    statuses[key] = state.get('personal_events', {}).get('status', '')
                elif key == 'work_status':
                    statuses[key] = state.get('work_events', {}).get('status', '')
                elif key == 'media_status':
                    statuses[key] = state.get('media_processed', {}).get('status', '')
                elif key == 'transcription_status':
                    statuses[key] = state.get('transcriptions', {}).get('status', '')
                elif key == 'notion_status':
                    statuses[key] = state.get('notion_synced', {}).get('status', '')
                else:
                    statuses[key] = ''
            return statuses
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения статусов: {e}")
            return {key: '' for key in self.STATUS_KEYS}
    
    def create_cycle_state(self, 
                          personal_stats: Dict[str, Any],
                          work_stats: Dict[str, Any],
                          media_stats: Dict[str, Any],
                          transcription_stats: Dict[str, Any],
                          notion_stats: Dict[str, Any],
                          summary_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает состояние цикла на основе статистики.
        
        Args:
            personal_stats: Статистика личного аккаунта
            work_stats: Статистика рабочего аккаунта
            media_stats: Статистика медиа
            transcription_stats: Статистика транскрипций
            notion_stats: Статистика Notion
            summary_stats: Статистика саммари
            
        Returns:
            Состояние цикла
        """
        try:
            # Извлекаем метрики из статистики
            personal_processed = personal_stats.get('processed', 0)
            work_processed = work_stats.get('processed', 0)
            media_count = media_stats.get('processed', 0)
            transcription_count = transcription_stats.get('processed', 0)
            notion_count = notion_stats.get('synced', 0)
            summary_count = summary_stats.get('processed', 0)
            
            # Подсчитываем общее количество ошибок
            total_errors = (
                personal_stats.get('errors', 0) +
                work_stats.get('errors', 0) +
                media_stats.get('errors', 0) +
                transcription_stats.get('errors', 0) +
                notion_stats.get('errors', 0) +
                summary_stats.get('errors', 0)
            )
            
            cycle_state = {
                'timestamp': self._get_current_timestamp(),
                'personal_events': {
                    'status': personal_stats.get('status', 'unknown'),
                    'processed': personal_processed,
                    'errors': personal_stats.get('errors', 0)
                },
                'work_events': {
                    'status': work_stats.get('status', 'unknown'),
                    'processed': work_processed,
                    'errors': work_stats.get('errors', 0)
                },
                'media_processed': {
                    'status': media_stats.get('status', 'unknown'),
                    'count': media_count,
                    'errors': media_stats.get('errors', 0)
                },
                'transcriptions': {
                    'status': transcription_stats.get('status', 'unknown'),
                    'count': transcription_count,
                    'errors': transcription_stats.get('errors', 0)
                },
                'notion_synced': {
                    'status': notion_stats.get('status', 'unknown'),
                    'count': notion_count,
                    'errors': notion_stats.get('errors', 0)
                },
                'summary_generated': {
                    'status': summary_stats.get('status', 'unknown'),
                    'count': summary_count,
                    'errors': summary_stats.get('errors', 0)
                },
                'errors_count': total_errors,
                'total_processed': personal_processed + work_processed + media_count + transcription_count + notion_count + summary_count
            }
            
            self.logger.info(f"📊 Создано состояние цикла: {cycle_state}")
            return cycle_state
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания состояния цикла: {e}")
            return {
                'timestamp': self._get_current_timestamp(),
                'errors_count': 1,
                'total_processed': 0
            }
    
    def _get_current_timestamp(self) -> str:
        """
        Получает текущий timestamp.
        
        Returns:
            Строка с текущим временем
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def compare_states(self, current: Dict[str, Any], previous: Dict[str, Any]) -> Dict[str, Any]:
        """
        Сравнивает два состояния и возвращает различия.
        
        Args:
            current: Текущее состояние
            previous: Предыдущее состояние
            
        Returns:
            Словарь с различиями
        """
        try:
            if not previous:
                return {'has_changes': True, 'reason': 'no_previous_state'}
            
            differences = {
                'has_changes': False,
                'differences': {},
                'summary': 'Изменений не обнаружено'
            }
            
            # Сравниваем метрики
            current_metrics = self._extract_metrics(current)
            previous_metrics = self._extract_metrics(previous)
            
            for key in self.METRIC_KEYS:
                if current_metrics[key] != previous_metrics[key]:
                    differences['differences'][key] = {
                        'previous': previous_metrics[key],
                        'current': current_metrics[key],
                        'change': current_metrics[key] - previous_metrics[key]
                    }
                    differences['has_changes'] = True
            
            # Формируем краткое описание изменений
            if differences['has_changes']:
                changes = []
                for key, diff in differences['differences'].items():
                    change = diff['change']
                    if change > 0:
                        changes.append(f"{key}: +{change}")
                    elif change < 0:
                        changes.append(f"{key}: {change}")
                
                differences['summary'] = f"Обнаружены изменения: {', '.join(changes)}"
            
            return differences
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сравнения состояний: {e}")
            return {'has_changes': True, 'reason': 'error_in_comparison', 'error': str(e)}
