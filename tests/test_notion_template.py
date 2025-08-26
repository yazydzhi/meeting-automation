#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки создания страницы в Notion с шаблоном.
"""

import os
from dotenv import load_dotenv
from src.notion_templates import create_customized_template, create_page_with_template

def test_template_creation():
    """Тестирует создание кастомизированного шаблона."""
    print("🧪 Тестирование создания шаблона...")
    
    # Тестовые данные
    title = "Тестовая встреча с шаблоном"
    start_time = "2025-08-21T10:00:00Z"
    end_time = "2025-08-21T11:00:00Z"
    attendees = ["test1@example.com", "test2@example.com"]
    meeting_link = "https://meet.google.com/test-meeting"
    drive_link = "https://drive.google.com/test-folder"
    
    try:
        # Создаем кастомизированный шаблон
        template = create_customized_template(
            title=title,
            start_time=start_time,
            end_time=end_time,
            attendees=attendees,
            meeting_link=meeting_link,
            drive_link=drive_link
        )
        
        print(f"✅ Шаблон создан успешно: {len(template['children'])} блоков")
        
        # Выводим структуру шаблона
        print("\n📋 Структура шаблона:")
        for i, block in enumerate(template['children']):
            block_type = block.get('type', 'unknown')
            if block_type == 'heading_1':
                content = block.get('heading_1', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                print(f"  {i+1}. H1: {content}")
            elif block_type == 'heading_2':
                content = block.get('heading_2', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                print(f"  {i+1}. H2: {content}")
            elif block_type == 'callout':
                content = block.get('callout', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                print(f"  {i+1}. Callout: {content}")
            elif block_type == 'paragraph':
                content = block.get('paragraph', {}).get('rich_text', [{}])[0].get('text', {}).get('content', '')
                print(f"  {i+1}. Paragraph: {content}")
            else:
                print(f"  {i+1}. {block_type}")
        
        return template
        
    except Exception as e:
        print(f"❌ Ошибка создания шаблона: {e}")
        return None

def test_page_creation():
    """Тестирует создание страницы в Notion (только если есть токен)."""
    load_dotenv()
    
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("⚠️ NOTION_TOKEN или NOTION_DATABASE_ID не найдены в .env")
        print("   Пропускаем тест создания страницы")
        return
    
    print("\n🧪 Тестирование создания страницы в Notion...")
    
    # Создаем тестовый шаблон
    template = create_customized_template(
        title="Тестовая встреча",
        start_time="2025-08-21T10:00:00Z",
        end_time="2025-08-21T11:00:00Z",
        attendees=["test@example.com"],
        meeting_link="https://meet.google.com/test",
        drive_link="https://drive.google.com/test"
    )
    
    # Свойства страницы
    properties = {
        "Name": {
            "title": [{"text": {"content": "Тестовая встреча"}}]
        },
        "Calendar": {
            "select": {"name": "Personal"}
        },
        "Event ID": {
            "rich_text": [{"text": {"content": "test-event-123"}}]
        }
    }
    
    try:
        page_id = create_page_with_template(
            notion_token=notion_token,
            database_id=database_id,
            properties=properties,
            template=template
        )
        
        if page_id:
            print(f"✅ Страница создана успешно: {page_id}")
            print(f"🔗 Ссылка: https://notion.so/{page_id.replace('-', '')}")
        else:
            print("❌ Не удалось создать страницу")
            
    except Exception as e:
        print(f"❌ Ошибка создания страницы: {e}")

if __name__ == "__main__":
    print("🚀 Тестирование системы шаблонов Notion\n")
    
    # Тест 1: Создание шаблона
    template = test_template_creation()
    
    if template:
        # Тест 2: Создание страницы (если есть токен)
        test_page_creation()
    
    print("\n✨ Тестирование завершено!")
