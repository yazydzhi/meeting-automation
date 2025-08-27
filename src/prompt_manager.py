#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер промптов для системы автоматизации встреч

TASK-3: Управление конфигурируемыми промптами для транскрипции, саммари и анализа
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from config.prompts import (
    TRANSCRIPTION_PROMPT,
    SUMMARY_PROMPT,
    ANALYSIS_PROMPT,
    COMPLEX_ANALYSIS_PROMPT,
    TITLE_GENERATION_PROMPT,
    KEYWORDS_EXTRACTION_PROMPT,
    SENTIMENT_ANALYSIS_PROMPT
)
from config.prompt_settings import (
    DEFAULT_PROMPT_SETTINGS,
    QUALITY_SETTINGS,
    LANGUAGE_SETTINGS,
    STYLE_SETTINGS,
    OUTPUT_FORMAT_SETTINGS
)


class PromptManager:
    """Менеджер для управления конфигурируемыми промптами."""
    
    def __init__(self, config_manager):
        """
        Инициализация менеджера промптов.
        
        Args:
            config_manager: Менеджер конфигурации
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Загружаем базовые промпты
        self.base_prompts = {
            'transcription': TRANSCRIPTION_PROMPT,
            'summary': SUMMARY_PROMPT,
            'analysis': ANALYSIS_PROMPT,
            'complex_analysis': COMPLEX_ANALYSIS_PROMPT,
            'title_generation': TITLE_GENERATION_PROMPT,
            'keywords_extraction': KEYWORDS_EXTRACTION_PROMPT,
            'sentiment_analysis': SENTIMENT_ANALYSIS_PROMPT
        }
        
        # Загружаем настройки по умолчанию
        self.default_settings = DEFAULT_PROMPT_SETTINGS
        self.quality_settings = QUALITY_SETTINGS
        self.language_settings = LANGUAGE_SETTINGS
        self.style_settings = STYLE_SETTINGS
        self.output_format_settings = OUTPUT_FORMAT_SETTINGS
        
        self.logger.info("🔧 PromptManager инициализирован")
    
    def get_prompt(self, prompt_type: str, custom_prompt: str = None) -> str:
        """
        Получить промпт указанного типа.
        
        Args:
            prompt_type: Тип промпта
            custom_prompt: Пользовательский промпт (если есть)
            
        Returns:
            Промпт для использования
        """
        try:
            # Проверяем, есть ли пользовательский промпт
            if custom_prompt and custom_prompt.strip():
                self.logger.info(f"🔧 Используется пользовательский промпт для {prompt_type}")
                return custom_prompt
            
            # Используем базовый промпт
            if prompt_type in self.base_prompts:
                self.logger.info(f"🔧 Используется базовый промпт для {prompt_type}")
                return self.base_prompts[prompt_type]
            else:
                self.logger.warning(f"⚠️ Неизвестный тип промпта: {prompt_type}")
                return ""
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения промпта {prompt_type}: {e}")
            return ""
    
    def get_prompt_settings(self, prompt_type: str) -> Dict[str, Any]:
        """
        Получить настройки для указанного типа промпта.
        
        Args:
            prompt_type: Тип промпта
            
        Returns:
            Настройки промпта
        """
        try:
            # Получаем настройки из конфигурации
            config_settings = self.config_manager.get_prompt_config(prompt_type)
            
            # Объединяем с настройками по умолчанию
            if prompt_type in self.default_settings:
                default = self.default_settings[prompt_type].copy()
                default.update(config_settings)
                return default
            else:
                return config_settings
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения настроек промпта {prompt_type}: {e}")
            return {}
    
    def get_quality_settings(self, quality_level: str = None) -> Dict[str, Any]:
        """
        Получить настройки качества.
        
        Args:
            quality_level: Уровень качества
            
        Returns:
            Настройки качества
        """
        try:
            if not quality_level:
                quality_level = self.config_manager.get_prompt_general_config().get('quality_level', 'balanced')
            
            if quality_level in self.quality_settings:
                return self.quality_settings[quality_level]
            else:
                self.logger.warning(f"⚠️ Неизвестный уровень качества: {quality_level}, используем balanced")
                return self.quality_settings['balanced']
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения настроек качества: {e}")
            return self.quality_settings['balanced']
    
    def get_language_settings(self, language: str = None) -> Dict[str, Any]:
        """
        Получить настройки языка.
        
        Args:
            language: Язык
            
        Returns:
            Настройки языка
        """
        try:
            if not language:
                language = self.config_manager.get_prompt_general_config().get('language', 'russian')
            
            if language in self.language_settings:
                return self.language_settings[language]
            else:
                self.logger.warning(f"⚠️ Неизвестный язык: {language}, используем russian")
                return self.language_settings['russian']
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения настроек языка: {e}")
            return self.language_settings['russian']
    
    def get_style_settings(self, style: str = None) -> Dict[str, Any]:
        """
        Получить настройки стиля.
        
        Args:
            style: Стиль
            
        Returns:
            Настройки стиля
        """
        try:
            if not style:
                style = self.config_manager.get_prompt_general_config().get('style', 'professional')
            
            if style in self.style_settings:
                return self.style_settings[style]
            else:
                self.logger.warning(f"⚠️ Неизвестный стиль: {style}, используем professional")
                return self.style_settings['professional']
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения настроек стиля: {e}")
            return self.style_settings['professional']
    
    def get_output_format_settings(self, output_format: str = None) -> Dict[str, Any]:
        """
        Получить настройки формата вывода.
        
        Args:
            output_format: Формат вывода
            
        Returns:
            Настройки формата вывода
        """
        try:
            if not output_format:
                output_format = self.config_manager.get_prompt_general_config().get('output_format', 'json')
            
            if output_format in self.output_format_settings:
                return self.output_format_settings[output_format]
            else:
                self.logger.warning(f"⚠️ Неизвестный формат вывода: {output_format}, используем json")
                return self.output_format_settings['json']
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения настроек формата вывода: {e}")
            return self.output_format_settings['json']
    
    def customize_prompt(self, base_prompt: str, customizations: Dict[str, Any]) -> str:
        """
        Кастомизировать базовый промпт.
        
        Args:
            base_prompt: Базовый промпт
            customizations: Кастомизации
            
        Returns:
            Кастомизированный промпт
        """
        try:
            customized_prompt = base_prompt
            
            # Применяем кастомизации
            for key, value in customizations.items():
                if isinstance(value, str) and value:
                    # Заменяем плейсхолдеры в промпте
                    placeholder = f"{{{key}}}"
                    if placeholder in customized_prompt:
                        customized_prompt = customized_prompt.replace(placeholder, str(value))
            
            self.logger.info(f"🔧 Промпт кастомизирован с {len(customizations)} параметрами")
            return customized_prompt
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка кастомизации промпта: {e}")
            return base_prompt
    
    def save_debug_prompt(self, prompt_type: str, prompt: str, settings: Dict[str, Any]):
        """
        Сохранить промпт для отладки.
        
        Args:
            prompt_type: Тип промпта
            prompt: Промпт
            settings: Настройки
        """
        try:
            general_config = self.config_manager.get_prompt_general_config()
            if not general_config.get('debug_save', False):
                return
            
            debug_dir = general_config.get('debug_dir', 'logs/prompts')
            os.makedirs(debug_dir, exist_ok=True)
            
            debug_file = Path(debug_dir) / f"{prompt_type}_debug_{int(os.time.time())}.json"
            
            debug_data = {
                "prompt_type": prompt_type,
                "timestamp": os.time.time(),
                "prompt": prompt,
                "settings": settings,
                "config_source": "prompt_manager"
            }
            
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"🔧 Промпт сохранен для отладки: {debug_file}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения промпта для отладки: {e}")
    
    def get_full_prompt_config(self, prompt_type: str) -> Dict[str, Any]:
        """
        Получить полную конфигурацию промпта.
        
        Args:
            prompt_type: Тип промпта
            
        Returns:
            Полная конфигурация
        """
        try:
            # Базовые настройки промпта
            prompt_settings = self.get_prompt_settings(prompt_type)
            
            # Общие настройки
            general_settings = self.config_manager.get_prompt_general_config()
            
            # Настройки качества
            quality_settings = self.get_quality_settings(general_settings.get('quality_level'))
            
            # Настройки языка
            language_settings = self.get_language_settings(general_settings.get('language'))
            
            # Настройки стиля
            style_settings = self.get_style_settings(general_settings.get('style'))
            
            # Настройки формата вывода
            output_format_settings = self.get_output_format_settings(general_settings.get('output_format'))
            
            # Объединяем все настройки
            full_config = {
                "prompt_type": prompt_type,
                "prompt_settings": prompt_settings,
                "general_settings": general_settings,
                "quality_settings": quality_settings,
                "language_settings": language_settings,
                "style_settings": style_settings,
                "output_format_settings": output_format_settings
            }
            
            return full_config
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения полной конфигурации промпта: {e}")
            return {}
    
    def validate_prompt_config(self, prompt_type: str) -> bool:
        """
        Валидировать конфигурацию промпта.
        
        Args:
            prompt_type: Тип промпта
            
        Returns:
            True если конфигурация валидна
        """
        try:
            config = self.get_full_prompt_config(prompt_type)
            
            # Проверяем обязательные поля
            required_fields = ['prompt_settings', 'general_settings']
            for field in required_fields:
                if field not in config or not config[field]:
                    self.logger.error(f"❌ Отсутствует обязательное поле: {field}")
                    return False
            
            # Проверяем настройки промпта
            prompt_settings = config['prompt_settings']
            if not prompt_settings.get('model'):
                self.logger.error(f"❌ Не указана модель для промпта {prompt_type}")
                return False
            
            self.logger.info(f"✅ Конфигурация промпта {prompt_type} валидна")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации конфигурации промпта: {e}")
            return False
    
    def list_available_prompts(self) -> List[str]:
        """
        Получить список доступных типов промптов.
        
        Returns:
            Список типов промптов
        """
        return list(self.base_prompts.keys())
    
    def get_prompt_info(self, prompt_type: str) -> Dict[str, Any]:
        """
        Получить информацию о промпте.
        
        Args:
            prompt_type: Тип промпта
            
        Returns:
            Информация о промпте
        """
        try:
            if prompt_type not in self.base_prompts:
                return {"error": f"Неизвестный тип промпта: {prompt_type}"}
            
            prompt = self.base_prompts[prompt_type]
            settings = self.get_prompt_settings(prompt_type)
            
            return {
                "type": prompt_type,
                "description": self._get_prompt_description(prompt_type),
                "length": len(prompt),
                "settings": settings,
                "available_customizations": list(settings.keys())
            }
            
        except Exception as e:
            return {"error": f"Ошибка получения информации: {e}"}
    
    def _get_prompt_description(self, prompt_type: str) -> str:
        """Получить описание промпта."""
        descriptions = {
            'transcription': 'Промпт для создания точной транскрипции аудиозаписи',
            'summary': 'Промпт для создания краткого саммари встречи',
            'analysis': 'Промпт для детального анализа транскрипции',
            'complex_analysis': 'Промпт для комплексного анализа нескольких встреч',
            'title_generation': 'Промпт для генерации заголовков',
            'keywords_extraction': 'Промпт для извлечения ключевых слов',
            'sentiment_analysis': 'Промпт для анализа тональности'
        }
        return descriptions.get(prompt_type, 'Описание недоступно')
