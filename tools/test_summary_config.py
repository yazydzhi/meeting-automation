#!/usr/bin/env python3
"""
Тестовый скрипт для проверки настроек саммари.
"""

import os
import sys

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager

def test_summary_config():
    """Тестирует загрузку настроек саммари."""
    print("🔍 Проверка настроек саммари...")
    
    config_manager = ConfigManager()
    summary_config = config_manager.get_summary_config()
    
    print(f"📊 Настройки саммари:")
    print(f"  🔧 ENABLE_GENERAL_SUMMARY: {summary_config.get('enable_general_summary', False)}")
    print(f"  🔧 ENABLE_COMPLEX_SUMMARY: {summary_config.get('enable_complex_summary', False)}")
    
    # Проверяем переменные окружения
    print(f"\n🌍 Переменные окружения:")
    print(f"  ENABLE_GENERAL_SUMMARY: {os.getenv('ENABLE_GENERAL_SUMMARY', 'не установлено')}")
    print(f"  ENABLE_COMPLEX_SUMMARY: {os.getenv('ENABLE_COMPLEX_SUMMARY', 'не установлено')}")

if __name__ == "__main__":
    test_summary_config()
