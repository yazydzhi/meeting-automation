#!/usr/bin/env python3
"""
Скрипт для тестирования добавления контента в Notion страницы.
Создает тестовые файлы и добавляет их в страницы Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_notion_content_adding():
    """Тестирует добавление контента в Notion страницы."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🧪 Тестирование добавления контента в Notion...")
    print("=" * 80)
    
    # Проверяем переменные окружения
    notion_token = os.getenv('NOTION_TOKEN')
    notion_database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not notion_database_id:
        print("❌ Не найдены переменные окружения NOTION_TOKEN или NOTION_DATABASE_ID")
        return False
    
    # Подключаемся к базе данных
    db_path = "data/system_state.db"
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем первое событие с Notion страницей
            cursor.execute('''
                SELECT 
                    pe.event_id,
                    pe.event_title,
                    nss.page_id
                FROM processed_events pe
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                WHERE nss.page_id IS NOT NULL
                ORDER BY pe.event_start_time DESC
                LIMIT 1
            ''')
            
            result = cursor.fetchone()
            
            if not result:
                print("❌ Не найдено событий с Notion страницами")
                return False
            
            event_id, event_title, page_id = result
            
            print(f"📋 Тестируем на событии: {event_title}")
            print(f"   🆔 Event ID: {event_id}")
            print(f"   📄 Page ID: {page_id}")
            print()
            
            # Настраиваем заголовки для Notion API
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            # 1. Тестируем добавление транскрипции
            print("📝 Тест 1: Добавление транскрипции")
            test_transcript_content = f"""Это тестовая транскрипция для события "{event_title}".

Встреча состоялась в рамках тестирования системы автоматизации встреч.

Основные темы обсуждения:
- Тестирование функциональности
- Проверка интеграции с Notion
- Валидация добавления контента

Участники активно обсуждали вопросы автоматизации и улучшения процессов.

Заключение: Тестирование прошло успешно, система работает корректно."""
            
            success1 = _add_test_content_to_page(page_id, "Транскрипция встречи", test_transcript_content, headers)
            print(f"   {'✅' if success1 else '❌'} Транскрипция {'добавлена' if success1 else 'не добавлена'}")
            print()
            
            # 2. Тестируем добавление саммари
            print("📊 Тест 2: Добавление саммари")
            test_summary_content = f"""Краткое резюме встречи "{event_title}":

🎯 Цель встречи: Тестирование системы автоматизации встреч

📋 Основные вопросы:
• Проверка функциональности добавления контента в Notion
• Валидация интеграции с базой данных
• Тестирование API Notion

✅ Результаты:
• Система успешно добавляет контент в страницы Notion
• Интеграция работает корректно
• API Notion отвечает без ошибок

📝 Следующие шаги:
• Продолжить тестирование с реальными данными
• Оптимизировать процесс добавления контента
• Добавить обработку ошибок"""
            
            success2 = _add_test_content_to_page(page_id, "Саммари и анализ", test_summary_content, headers)
            print(f"   {'✅' if success2 else '❌'} Саммари {'добавлено' if success2 else 'не добавлено'}")
            print()
            
            # 3. Тестируем добавление анализа
            print("🔍 Тест 3: Добавление анализа")
            test_analysis_content = f"""Детальный анализ встречи "{event_title}":

📈 Анализ эффективности:
• Время проведения: оптимальное для тестирования
• Участники: заинтересованы в результатах
• Качество обсуждения: высокое

🎯 Ключевые инсайты:
• Система автоматизации работает стабильно
• Интеграция с Notion функционирует корректно
• Процесс добавления контента оптимизирован

⚠️ Выявленные проблемы:
• Отсутствуют (тестирование прошло без ошибок)
• Все компоненты работают как ожидается

💡 Рекомендации:
• Продолжить использование системы в продакшене
• Регулярно обновлять контент в Notion
• Мониторить производительность API

📊 Метрики:
• Время выполнения: < 1 секунды
• Успешность операций: 100%
• Качество контента: высокое"""
            
            success3 = _add_test_content_to_page(page_id, "Детальный анализ", test_analysis_content, headers)
            print(f"   {'✅' if success3 else '❌'} Анализ {'добавлен' if success3 else 'не добавлен'}")
            print()
            
            # 4. Проверяем результат
            print("🔍 Тест 4: Проверка результата")
            success4 = _check_page_content(page_id, headers)
            print(f"   {'✅' if success4 else '❌'} Контент {'найден' if success4 else 'не найден'}")
            print()
            
            # Итоги
            total_tests = 4
            passed_tests = sum([success1, success2, success3, success4])
            
            print(f"📊 Результаты тестирования:")
            print(f"   ✅ Пройдено: {passed_tests}/{total_tests} тестов")
            print(f"   📈 Успешность: {passed_tests/total_tests*100:.1f}%")
            
            if passed_tests == total_tests:
                print("   🎉 Все тесты пройдены успешно!")
                return True
            else:
                print("   ⚠️ Некоторые тесты не пройдены")
                return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def _add_test_content_to_page(page_id: str, content_type: str, content: str, headers: dict) -> bool:
    """Добавляет тестовый контент в страницу Notion."""
    
    try:
        # Определяем тип заголовка
        if "Транскрипция" in content_type:
            heading_emoji = "📝"
            heading_text = "Транскрипция встречи"
        elif "Саммари" in content_type:
            heading_emoji = "📊"
            heading_text = "Саммари и анализ"
        elif "анализ" in content_type.lower():
            heading_emoji = "🔍"
            heading_text = "Детальный анализ"
        else:
            heading_emoji = "📋"
            heading_text = content_type
        
        # Формируем блоки
        blocks = [
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"{heading_emoji} {heading_text}"
                            }
                        }
                    ]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            }
        ]
        
        # Добавляем блоки в страницу
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_data = {"children": blocks}
        
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        response.raise_for_status()
        
        return True
        
    except Exception as e:
        print(f"   ❌ Ошибка добавления {content_type}: {e}")
        return False

def _check_page_content(page_id: str, headers: dict) -> bool:
    """Проверяет наличие контента на странице."""
    
    try:
        # Получаем блоки страницы
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=headers)
        blocks_response.raise_for_status()
        blocks_data = blocks_response.json()
        
        blocks = blocks_data.get('results', [])
        
        # Проверяем наличие контента
        has_transcription = False
        has_summary = False
        has_analysis = False
        
        for block in blocks:
            if block.get('type') == 'heading_2':
                heading_text = block.get('heading_2', {}).get('rich_text', [])
                if heading_text:
                    text_content = heading_text[0].get('text', {}).get('content', '')
                    if 'Транскрипция' in text_content:
                        has_transcription = True
                    elif 'Саммари' in text_content:
                        has_summary = True
                    elif 'анализ' in text_content.lower():
                        has_analysis = True
        
        print(f"      📝 Транскрипция: {'✅' if has_transcription else '❌'}")
        print(f"      📊 Саммари: {'✅' if has_summary else '❌'}")
        print(f"      🔍 Анализ: {'✅' if has_analysis else '❌'}")
        
        return has_transcription and has_summary and has_analysis
        
    except Exception as e:
        print(f"   ❌ Ошибка проверки контента: {e}")
        return False

if __name__ == "__main__":
    success = test_notion_content_adding()
    
    if success:
        print("✅ Тестирование завершено успешно!")
    else:
        print("❌ Тестирование завершено с ошибками!")
        sys.exit(1)
