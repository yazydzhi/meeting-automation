#!/usr/bin/env python3
"""
Скрипт для проверки схемы базы данных Notion.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_notion_database_schema():
    """Проверяет схему базы данных Notion."""
    
    # Получаем токен из переменных окружения
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("❌ Не найдены переменные окружения NOTION_TOKEN или NOTION_DATABASE_ID")
        return False
    
    try:
        # Настраиваем заголовки для API
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        print("🗄️ Проверка схемы базы данных Notion...")
        print("=" * 60)
        
        # Получаем информацию о базе данных
        url = f"https://api.notion.com/v1/databases/{database_id}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        database_info = response.json()
        properties = database_info.get('properties', {})
        
        print(f"📊 База данных: {database_info.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
        print(f"📊 ID базы данных: {database_id}")
        print()
        
        print("📋 Свойства базы данных:")
        print("-" * 60)
        
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get('type', 'unknown')
            print(f"  • {prop_name:<20} | Тип: {prop_type}")
            
            # Показываем дополнительную информацию для некоторых типов
            if prop_type == 'date':
                print(f"    └─ Поле даты (может содержать start и end)")
            elif prop_type == 'rich_text':
                print(f"    └─ Текстовое поле")
            elif prop_type == 'title':
                print(f"    └─ Заголовок страницы")
            elif prop_type == 'select':
                options = prop_info.get('select', {}).get('options', [])
                if options:
                    option_names = [opt.get('name', '') for opt in options]
                    print(f"    └─ Варианты: {', '.join(option_names)}")
            elif prop_type == 'url':
                print(f"    └─ URL поле")
        
        print()
        
        # Проверяем, есть ли отдельные поля для времени начала и окончания
        has_start_time = any('start' in name.lower() or 'begin' in name.lower() for name in properties.keys())
        has_end_time = any('end' in name.lower() or 'finish' in name.lower() for name in properties.keys())
        
        print("🔍 Анализ полей времени:")
        print(f"  📅 Поле Date: {'✅' if 'Date' in properties else '❌'}")
        print(f"  🕐 Поле Start Time: {'✅' if has_start_time else '❌'}")
        print(f"  🕐 Поле End Time: {'✅' if has_end_time else '❌'}")
        
        if 'Date' in properties:
            date_prop = properties['Date']
            if date_prop.get('type') == 'date':
                print(f"  📅 Date - это поле даты (может содержать start и end)")
        
        print()
        
        # Проверяем пример страницы
        print("📄 Пример страницы:")
        print("-" * 60)
        
        # Получаем первую страницу для примера
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        payload = {"page_size": 1}
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if data.get('results'):
            page = data['results'][0]
            page_properties = page.get('properties', {})
            
            # Показываем свойства первой страницы
            for prop_name, prop_info in page_properties.items():
                prop_type = prop_info.get('type', 'unknown')
                
                if prop_type == 'title' and prop_info.get('title'):
                    title = prop_info['title'][0]['text']['content']
                    print(f"  📝 {prop_name}: {title}")
                elif prop_type == 'date' and prop_info.get('date'):
                    date_info = prop_info['date']
                    start_date = date_info.get('start', '')
                    end_date = date_info.get('end', '')
                    print(f"  📅 {prop_name}: {start_date} {'→ ' + end_date if end_date else ''}")
                elif prop_type == 'rich_text' and prop_info.get('rich_text'):
                    text = prop_info['rich_text'][0]['text']['content']
                    print(f"  📄 {prop_name}: {text[:50]}{'...' if len(text) > 50 else ''}")
                elif prop_type == 'url' and prop_info.get('url'):
                    url = prop_info['url']
                    print(f"  🔗 {prop_name}: {url[:50]}{'...' if len(url) > 50 else ''}")
                elif prop_type == 'select' and prop_info.get('select'):
                    select_name = prop_info['select'].get('name', '')
                    print(f"  🏷️ {prop_name}: {select_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке схемы базы данных Notion: {e}")
        return False

if __name__ == "__main__":
    success = check_notion_database_schema()
    
    if success:
        print("\n✅ Проверка схемы базы данных завершена успешно!")
    else:
        print("\n❌ Проверка завершена с ошибками!")
        sys.exit(1)
