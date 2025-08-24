#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки TranscriptAnalyzer
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from transcript_analyzer import TranscriptAnalyzer
from config_manager import ConfigManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_transcript_analyzer():
    """Тестирует работу TranscriptAnalyzer"""
    
    print("🧪 Тестирую TranscriptAnalyzer...")
    
    # Загружаем конфигурацию
    config_manager = ConfigManager('env.work')
    
    # Получаем настройки OpenAI
    openai_config = config_manager.config.get('openai', {})
    api_key = openai_config.get('api_key')
    model = openai_config.get('analysis_model', 'gpt-4o-mini')
    
    if not api_key:
        print("❌ OPENAI_API_KEY не найден в конфигурации")
        return False
    
    print(f"🔑 OpenAI API ключ: {api_key[:20]}...")
    print(f"🤖 Модель: {model}")
    
    # Создаем анализатор
    analyzer = TranscriptAnalyzer(api_key, model)
    
    # Тестовый текст транскрипции
    test_transcript = """
    Добро пожаловать на встречу по проекту "Альфа неипотечные сделки вторичка".
    
    Денис Кузнецов: Добрый день, коллеги. Сегодня мы обсуждаем план развития проекта на следующий квартал.
    
    Мария Иванова: Согласна, нам нужно увеличить бюджет на маркетинг минимум на 20%.
    
    Денис Кузнецов: Хорошо, я подготовлю презентацию для руководства. Срок - до пятницы.
    
    Петр Сидоров: А что с техническими задачами? Нужно завершить интеграцию с банками до конца месяца.
    
    Денис Кузнецов: Верно, это приоритет. Петр, возьми на себя контроль по техническим вопросам.
    
    Мария Иванова: А бюджет на рекламу? Когда будет решение?
    
    Денис Кузнецов: В понедельник встреча с финансовым директором. Ожидаю положительного решения.
    
    Петр Сидоров: Отлично. Тогда мы сможем запустить новую кампанию уже в следующем месяце.
    
    Денис Кузнецов: Итак, резюмируем: Петр контролирует техническую часть, я готовлю презентацию, Мария ждет решения по бюджету.
    """
    
    print(f"\n📝 Тестовая транскрипция ({len(test_transcript)} символов):")
    print("-" * 50)
    print(test_transcript[:200] + "..." if len(test_transcript) > 200 else test_transcript)
    print("-" * 50)
    
    # Анализируем транскрипцию
    print("\n🔍 Анализирую транскрипцию...")
    
    try:
        analysis_result = analyzer.analyze_meeting_transcript(
            test_transcript,
            "Альфа неипотечные сделки вторичка - Планирование",
            "2025-01-27"
        )
        
        print("✅ Анализ завершен успешно!")
        
        # Сохраняем результат в файл
        output_file = "test_analysis_result.json"
        if analyzer.save_analysis_to_file(analysis_result, output_file):
            print(f"💾 Результат сохранен в: {output_file}")
        
        # Создаем данные для Notion
        print("\n📝 Создаю данные для Notion...")
        notion_data = analyzer.create_notion_page_data(analysis_result)
        
        if notion_data:
            print("✅ Данные для Notion созданы успешно!")
            
            # Сохраняем данные для Notion
            notion_file = "test_notion_page_data.json"
            with open(notion_file, 'w', encoding='utf-8') as f:
                import json
                json.dump(notion_data, f, ensure_ascii=False, indent=2)
            print(f"💾 Данные для Notion сохранены в: {notion_file}")
        
        # Показываем краткий результат
        print("\n📊 Краткий результат анализа:")
        summary = analysis_result.get('meeting_summary', {})
        print(f"   Название: {summary.get('title', 'Не указано')}")
        print(f"   Основная тема: {summary.get('main_topic', 'Не указано')}")
        print(f"   Ключевые решения: {len(summary.get('key_decisions', []))}")
        print(f"   Действия: {len(summary.get('action_items', []))}")
        print(f"   Темы обсуждения: {len(analysis_result.get('topics_discussed', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при анализе: {e}")
        return False

def main():
    """Основная функция"""
    print("🚀 Запуск тестирования TranscriptAnalyzer")
    print("=" * 50)
    
    success = test_transcript_analyzer()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Тестирование завершено успешно!")
    else:
        print("❌ Тестирование завершено с ошибками!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
