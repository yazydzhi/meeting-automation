#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Настройки промптов по умолчанию для системы автоматизации встреч

TASK-3: Конфигурационные параметры для промптов
"""

# Настройки по умолчанию для промптов
DEFAULT_PROMPT_SETTINGS = {
    # Настройки транскрипции
    "transcription": {
        "temperature": 0.1,  # Низкая температура для точности
        "max_tokens": 4000,
        "model": "whisper-1",
        "language": "ru",
        "include_timestamps": True,
        "speaker_detection": True,
        "quality_notes": True
    },
    
    # Настройки саммари
    "summary": {
        "temperature": 0.3,  # Умеренная креативность
        "max_tokens": 2000,
        "model": "gpt-4o-mini",
        "style": "professional",
        "include_actions": True,
        "include_deadlines": True,
        "include_risks": True,
        "max_length": "medium"  # short, medium, long
    },
    
    # Настройки анализа
    "analysis": {
        "temperature": 0.2,  # Низкая температура для структурированности
        "max_tokens": 4000,
        "model": "gpt-4o-mini",
        "include_financial": True,
        "include_quotes": True,
        "include_metrics": True,
        "include_risks": True,
        "output_format": "json"
    },
    
    # Настройки комплексного анализа
    "complex_analysis": {
        "temperature": 0.4,  # Средняя креативность для выявления трендов
        "max_tokens": 6000,
        "model": "gpt-4o-mini",
        "include_trends": True,
        "include_progress": True,
        "include_recurring": True,
        "include_insights": True,
        "max_meetings": 10  # Максимальное количество встреч для анализа
    },
    
    # Настройки генерации заголовков
    "title_generation": {
        "temperature": 0.5,  # Средняя креативность для заголовков
        "max_tokens": 100,
        "model": "gpt-4o-mini",
        "style": "professional",
        "max_words": 15,
        "include_date": False,
        "include_project": True
    },
    
    # Настройки извлечения ключевых слов
    "keywords_extraction": {
        "temperature": 0.1,  # Низкая температура для точности
        "max_tokens": 1000,
        "model": "gpt-4o-mini",
        "max_keywords": 20,
        "include_abbreviations": True,
        "include_technical": True,
        "include_business": True
    },
    
    # Настройки анализа тональности
    "sentiment_analysis": {
        "temperature": 0.2,  # Низкая температура для объективности
        "max_tokens": 2000,
        "model": "gpt-4o-mini",
        "include_emotions": True,
        "include_conflicts": True,
        "include_collaboration": True,
        "confidence_threshold": 0.7
    }
}

# Настройки качества и производительности
QUALITY_SETTINGS = {
    "high_quality": {
        "model": "gpt-4o",
        "temperature": 0.1,
        "max_tokens": 8000,
        "timeout": 120
    },
    "balanced": {
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 4000,
        "timeout": 60
    },
    "fast": {
        "model": "gpt-3.5-turbo",
        "temperature": 0.5,
        "max_tokens": 2000,
        "timeout": 30
    }
}

# Настройки языков
LANGUAGE_SETTINGS = {
    "russian": {
        "code": "ru",
        "name": "Русский",
        "formal": True,
        "business_style": True
    },
    "english": {
        "code": "en",
        "name": "English",
        "formal": True,
        "business_style": True
    },
    "mixed": {
        "code": "auto",
        "name": "Автоопределение",
        "formal": True,
        "business_style": True
    }
}

# Настройки стилей
STYLE_SETTINGS = {
    "professional": {
        "tone": "formal",
        "vocabulary": "business",
        "structure": "structured",
        "examples": False
    },
    "casual": {
        "tone": "informal",
        "vocabulary": "everyday",
        "structure": "flexible",
        "examples": True
    },
    "technical": {
        "tone": "precise",
        "vocabulary": "technical",
        "structure": "detailed",
        "examples": True
    },
    "executive": {
        "tone": "formal",
        "vocabulary": "executive",
        "structure": "concise",
        "examples": False
    }
}

# Настройки форматов вывода
OUTPUT_FORMAT_SETTINGS = {
    "json": {
        "format": "json",
        "indent": 2,
        "ensure_ascii": False,
        "sort_keys": True
    },
    "markdown": {
        "format": "markdown",
        "headers": True,
        "lists": True,
        "tables": True
    },
    "text": {
        "format": "text",
        "paragraphs": True,
        "bullet_points": True,
        "structure": True
    },
    "html": {
        "format": "html",
        "tags": True,
        "css_classes": True,
        "responsive": True
    }
}

# Экспорт всех настроек
__all__ = [
    'DEFAULT_PROMPT_SETTINGS',
    'QUALITY_SETTINGS',
    'LANGUAGE_SETTINGS',
    'STYLE_SETTINGS',
    'OUTPUT_FORMAT_SETTINGS'
]
