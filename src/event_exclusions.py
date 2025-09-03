#!/usr/bin/env python3
"""
Модуль для работы с исключениями событий календаря.
Поддерживает ключевые слова и регулярные выражения.
"""

import re
import os
from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum


class ExclusionType(Enum):
    """Типы исключений."""
    KEYWORD = "keyword"
    REGEX = "regex"


@dataclass
class EventExclusion:
    """Исключение события."""
    account_type: str  # personal, work, both
    exclusion_type: ExclusionType
    value: str
    compiled_regex: Optional[re.Pattern] = None
    
    def __post_init__(self):
        """Компилируем регулярное выражение после создания объекта."""
        if self.exclusion_type == ExclusionType.REGEX:
            try:
                self.compiled_regex = re.compile(self.value, re.IGNORECASE)
            except re.error as e:
                raise ValueError(f"Неверное регулярное выражение '{self.value}': {e}")


class EventExclusionManager:
    """Менеджер исключений событий календаря."""
    
    def __init__(self, config_manager=None, logger=None):
        """
        Инициализация менеджера исключений.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        self.config_manager = config_manager
        self.logger = logger
        self.exclusions: List[EventExclusion] = []
        self._load_exclusions()
    
    def _load_exclusions(self):
        """Загружает исключения из конфигурации."""
        try:
            # Если config_manager не предоставлен, загружаем напрямую из переменных окружения
            if not self.config_manager:
                if self.logger:
                    self.logger.info("📝 ConfigManager не предоставлен, загружаю исключения из переменных окружения")
            
            # Получаем исключения из переменной окружения
            exclusions_str = os.getenv('EVENT_EXCLUSIONS', '')
            if not exclusions_str:
                if self.logger:
                    self.logger.info("📝 EVENT_EXCLUSIONS не настроен, исключения не загружены")
                return
            
            # Парсим исключения
            exclusions_list = [exclusion.strip() for exclusion in exclusions_str.split(',') if exclusion.strip()]
            
            for exclusion_str in exclusions_list:
                try:
                    exclusion = self._parse_exclusion(exclusion_str)
                    if exclusion:
                        self.exclusions.append(exclusion)
                except Exception as e:
                    if self.logger:
                        self.logger.error(f"❌ Ошибка парсинга исключения '{exclusion_str}': {e}")
                    continue
            
            if self.logger:
                self.logger.info(f"✅ Загружено {len(self.exclusions)} исключений событий")
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка загрузки исключений: {e}")
    
    def _parse_exclusion(self, exclusion_str: str) -> Optional[EventExclusion]:
        """
        Парсит строку исключения.
        
        Args:
            exclusion_str: Строка в формате "account_type:exclusion_type:value"
            
        Returns:
            Объект исключения или None
        """
        parts = exclusion_str.split(':', 2)
        if len(parts) != 3:
            raise ValueError(f"Неверный формат исключения: {exclusion_str}")
        
        account_type, exclusion_type_str, value = parts
        
        # Проверяем тип аккаунта
        if account_type not in ['personal', 'work', 'both']:
            raise ValueError(f"Неверный тип аккаунта: {account_type}")
        
        # Проверяем тип исключения
        try:
            exclusion_type = ExclusionType(exclusion_type_str)
        except ValueError:
            raise ValueError(f"Неверный тип исключения: {exclusion_type_str}")
        
        return EventExclusion(
            account_type=account_type,
            exclusion_type=exclusion_type,
            value=value
        )
    
    def should_exclude_event(self, event_title: str, account_type: str) -> bool:
        """
        Проверяет, должно ли событие быть исключено.
        
        Args:
            event_title: Название события
            account_type: Тип аккаунта (personal, work)
            
        Returns:
            True если событие должно быть исключено
        """
        if not event_title or not self.exclusions:
            return False
        
        for exclusion in self.exclusions:
            # Проверяем, применимо ли исключение к данному типу аккаунта
            if exclusion.account_type not in ['both', account_type]:
                continue
            
            # Проверяем исключение
            if exclusion.exclusion_type == ExclusionType.KEYWORD:
                if exclusion.value.lower() in event_title.lower():
                    if self.logger:
                        self.logger.info(f"🚫 Событие исключено по ключевому слову: '{event_title}' содержит '{exclusion.value}'")
                    return True
            
            elif exclusion.exclusion_type == ExclusionType.REGEX:
                if exclusion.compiled_regex and exclusion.compiled_regex.search(event_title):
                    if self.logger:
                        self.logger.info(f"🚫 Событие исключено по регулярному выражению: '{event_title}' соответствует '{exclusion.value}'")
                    return True
        
        return False
    
    def get_exclusions_for_account(self, account_type: str) -> List[EventExclusion]:
        """
        Получает исключения для указанного типа аккаунта.
        
        Args:
            account_type: Тип аккаунта (personal, work)
            
        Returns:
            Список исключений для аккаунта
        """
        return [
            exclusion for exclusion in self.exclusions
            if exclusion.account_type in ['both', account_type]
        ]
    
    def get_exclusion_stats(self) -> Dict[str, int]:
        """
        Получает статистику исключений.
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            'total': len(self.exclusions),
            'personal': 0,
            'work': 0,
            'both': 0,
            'keywords': 0,
            'regex': 0
        }
        
        for exclusion in self.exclusions:
            stats[exclusion.account_type] += 1
            stats[f"{exclusion.exclusion_type.value}s"] += 1
        
        return stats
    
    def add_exclusion(self, account_type: str, exclusion_type: ExclusionType, value: str) -> bool:
        """
        Добавляет новое исключение.
        
        Args:
            account_type: Тип аккаунта
            exclusion_type: Тип исключения
            value: Значение исключения
            
        Returns:
            True если исключение добавлено успешно
        """
        try:
            exclusion = EventExclusion(
                account_type=account_type,
                exclusion_type=exclusion_type,
                value=value
            )
            self.exclusions.append(exclusion)
            
            if self.logger:
                self.logger.info(f"✅ Добавлено исключение: {account_type}:{exclusion_type.value}:{value}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка добавления исключения: {e}")
            return False
    
    def remove_exclusion(self, account_type: str, exclusion_type: ExclusionType, value: str) -> bool:
        """
        Удаляет исключение.
        
        Args:
            account_type: Тип аккаунта
            exclusion_type: Тип исключения
            value: Значение исключения
            
        Returns:
            True если исключение удалено
        """
        for i, exclusion in enumerate(self.exclusions):
            if (exclusion.account_type == account_type and 
                exclusion.exclusion_type == exclusion_type and 
                exclusion.value == value):
                
                del self.exclusions[i]
                
                if self.logger:
                    self.logger.info(f"✅ Удалено исключение: {account_type}:{exclusion_type.value}:{value}")
                
                return True
        
        return False
    
    def reload_exclusions(self):
        """Перезагружает исключения из конфигурации."""
        self.exclusions.clear()
        self._load_exclusions()
        
        if self.logger:
            self.logger.info("🔄 Исключения перезагружены")
    
    def __str__(self) -> str:
        """Строковое представление менеджера исключений."""
        if not self.exclusions:
            return "Исключения не настроены"
        
        lines = ["Настроенные исключения:"]
        for exclusion in self.exclusions:
            lines.append(f"  {exclusion.account_type}:{exclusion.exclusion_type.value}:{exclusion.value}")
        
        return "\n".join(lines)
