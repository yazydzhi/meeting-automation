#!/usr/bin/env python3
"""
Скрипт для отладки поля Date в Notion.
"""

import os
import sys
import requests
from dotenv import load_dotenv
import json

# Загружаем переменные окружения
load_dotenv()

def debug_notion_date_field():
    """Отлаживает поле Date в Notion."""
    
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
        
        print("🔍 Отладка поля Date в Notion...")
        print("=" * 60)
        
        # Получаем первые 3 страницы для детального анализа
        url = f"https://api.notion.com/v1/databases/{database_id}/query"
        payload = {
            "page_size": 3
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        data = response.json()
        pages = data.get('results', [])
        
        print(f"📊 Анализируем {len(pages)} страниц:")
        print()
        
        for i, page in enumerate(pages, 1):
            page_id = page['id']
            properties = page['properties']
            
            # Получаем название страницы
            title = ""
            if 'Name' in properties:
                title_prop = properties['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            print(f"📄 Страница {i}: {title}")
            print(f"   ID: {page_id}")
            
            # Анализируем поле Date
            if 'Date' in properties:
                date_prop = properties['Date']
                print(f"   📅 Поле Date:")
                print(f"      Тип: {date_prop.get('type', 'unknown')}")
                
                if date_prop.get('date'):
                    date_info = date_prop['date']
                    print(f"      Содержимое: {json.dumps(date_info, indent=8, ensure_ascii=False)}")
                    
                    start_date = date_info.get('start', '')
                    end_date = date_info.get('end', '')
                    
                    print(f"      🕐 Время начала: {start_date}")
                    print(f"      🕐 Время окончания: {end_date if end_date else 'ОТСУТСТВУЕТ'}")
                    
                    if end_date:
                        print(f"      ✅ Время окончания присутствует")
                    else:
                        print(f"      ❌ Время окончания отсутствует")
                else:
                    print(f"      ❌ Поле date пустое или отсутствует")
            else:
                print(f"   ❌ Поле Date отсутствует")
            
            print()
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при отладке поля Date в Notion: {e}")
        return False

if __name__ == "__main__":
    success = debug_notion_date_field()
    
    if success:
        print("✅ Отладка поля Date завершена успешно!")
    else:
        print("❌ Отладка завершена с ошибками!")
        sys.exit(1)
