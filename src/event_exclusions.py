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
            exclusion_str: Строка исключения (ключевое слово или "regex:pattern")
            
        Returns:
            Объект исключения или None
        """
        exclusion_str = exclusion_str.strip()
        if not exclusion_str:
            return None
        
        # Проверяем, является ли это регулярным выражением
        if exclusion_str.startswith('regex:'):
            pattern = exclusion_str[6:]  # Убираем "regex:"
            if not pattern:
                raise ValueError("Пустое регулярное выражение")
            
            return EventExclusion(
                exclusion_type=ExclusionType.REGEX,
                value=pattern
            )
        else:
            # Обычное ключевое слово
            return EventExclusion(
                exclusion_type=ExclusionType.KEYWORD,
                value=exclusion_str
            )
    
    def should_exclude_event(self, event_title: str, account_type: str = None) -> bool:
        """
        Проверяет, должно ли событие быть исключено.
        
        Args:
            event_title: Название события
            account_type: Тип аккаунта (игнорируется, оставлен для совместимости)
            
        Returns:
            True если событие должно быть исключено
        """
        if not event_title or not self.exclusions:
            return False
        
        for exclusion in self.exclusions:
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
    
    def get_all_exclusions(self) -> List[EventExclusion]:
        """
        Получает все исключения.
        
        Returns:
            Список всех исключений
        """
        return self.exclusions.copy()
    
    def get_exclusion_stats(self) -> Dict[str, int]:
        """
        Получает статистику исключений.
        
        Returns:
            Словарь со статистикой
        """
        stats = {
            'total': len(self.exclusions),
            'keywords': 0,
            'regex': 0
        }
        
        for exclusion in self.exclusions:
            if exclusion.exclusion_type == ExclusionType.KEYWORD:
                stats['keywords'] += 1
            elif exclusion.exclusion_type == ExclusionType.REGEX:
                stats['regex'] += 1
        
        return stats
    
    def add_exclusion(self, exclusion_type: ExclusionType, value: str) -> bool:
        """
        Добавляет новое исключение.
        
        Args:
            exclusion_type: Тип исключения
            value: Значение исключения
            
        Returns:
            True если исключение добавлено успешно
        """
        try:
            exclusion = EventExclusion(
                exclusion_type=exclusion_type,
                value=value
            )
            self.exclusions.append(exclusion)
            
            if self.logger:
                self.logger.info(f"✅ Добавлено исключение: {exclusion_type.value}:{value}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ Ошибка добавления исключения: {e}")
            return False
    
    def remove_exclusion(self, exclusion_type: ExclusionType, value: str) -> bool:
        """
        Удаляет исключение.
        
        Args:
            exclusion_type: Тип исключения
            value: Значение исключения
            
        Returns:
            True если исключение удалено
        """
        for i, exclusion in enumerate(self.exclusions):
            if (exclusion.exclusion_type == exclusion_type and 
                exclusion.value == value):
                
                del self.exclusions[i]
                
                if self.logger:
                    self.logger.info(f"✅ Удалено исключение: {exclusion_type.value}:{value}")
                
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
            if exclusion.exclusion_type == ExclusionType.REGEX:
                lines.append(f"  regex:{exclusion.value}")
            else:
                lines.append(f"  {exclusion.value}")
        
        return "\n".join(lines)
