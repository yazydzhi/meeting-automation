#!/usr/bin/env python3
"""
Скрипт для проверки дубликатов в Notion через API.
"""

import os
import sys
import requests
from collections import defaultdict
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_notion_api_duplicates():
    """Проверяет дубликаты в Notion через API."""
    
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
        
        print("🔍 Проверка дубликатов в Notion через API...")
        print("=" * 60)
        
        # Получаем все страницы из базы данных
        all_pages = []
        has_more = True
        start_cursor = None
        
        while has_more:
            url = f"https://api.notion.com/v1/databases/{database_id}/query"
            payload = {
                "page_size": 100
            }
            if start_cursor:
                payload["start_cursor"] = start_cursor
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            all_pages.extend(data['results'])
            has_more = data['has_more']
            start_cursor = data.get('next_cursor')
        
        print(f"📊 Всего страниц в Notion: {len(all_pages)}")
        
        # Анализируем дубликаты по названию
        title_counts = defaultdict(list)
        event_id_counts = defaultdict(list)
        
        for page in all_pages:
            # Получаем название страницы
            title = ""
            if 'properties' in page and 'Name' in page['properties']:
                title_prop = page['properties']['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            # Получаем Event ID
            event_id = ""
            if 'properties' in page and 'Event ID' in page['properties']:
                event_id_prop = page['properties']['Event ID']
                if event_id_prop['type'] == 'rich_text' and event_id_prop['rich_text']:
                    event_id = event_id_prop['rich_text'][0]['text']['content']
            
            page_id = page['id']
            created_time = page['created_time']
            
            title_counts[title].append({
                'page_id': page_id,
                'title': title,
                'event_id': event_id,
                'created_time': created_time
            })
            
            if event_id:
                event_id_counts[event_id].append({
                    'page_id': page_id,
                    'title': title,
                    'event_id': event_id,
                    'created_time': created_time
                })
        
        # Проверяем дубликаты по названию
        print("\n🔍 Анализ дубликатов по названию:")
        print("-" * 40)
        title_duplicates = {k: v for k, v in title_counts.items() if len(v) > 1 and k}
        
        if title_duplicates:
            print(f"❌ Найдено {len(title_duplicates)} названий с дубликатами:")
            for title, pages in title_duplicates.items():
                print(f"\n  Название: '{title}'")
                for page in pages:
                    print(f"    Page ID: {page['page_id']}, Event ID: {page['event_id']}, Created: {page['created_time']}")
        else:
            print("✅ Дубликатов по названию не найдено")
        
        # Проверяем дубликаты по Event ID
        print("\n🔍 Анализ дубликатов по Event ID:")
        print("-" * 40)
        event_duplicates = {k: v for k, v in event_id_counts.items() if len(v) > 1}
        
        if event_duplicates:
            print(f"❌ Найдено {len(event_duplicates)} Event ID с дубликатами:")
            for event_id, pages in event_duplicates.items():
                print(f"\n  Event ID: {event_id}")
                for page in pages:
                    print(f"    Page ID: {page['page_id']}, Title: '{page['title']}', Created: {page['created_time']}")
        else:
            print("✅ Дубликатов по Event ID не найдено")
        
        # Проверяем страницы с пустыми Event ID
        print("\n🔍 Анализ страниц с пустыми Event ID:")
        print("-" * 40)
        empty_event_id_pages = [page for page in all_pages 
                               if not page.get('properties', {}).get('Event ID', {}).get('rich_text')]
        
        if empty_event_id_pages:
            print(f"❌ Найдено {len(empty_event_id_pages)} страниц с пустыми Event ID:")
            for page in empty_event_id_pages:
                title = ""
                if 'properties' in page and 'Name' in page['properties']:
                    title_prop = page['properties']['Name']
                    if title_prop['type'] == 'title' and title_prop['title']:
                        title = title_prop['title'][0]['text']['content']
                print(f"    Page ID: {page['id']}, Title: '{title}', Created: {page['created_time']}")
        else:
            print("✅ Все страницы имеют Event ID")
        
        # Статистика
        print("\n📊 Статистика:")
        print("-" * 20)
        print(f"Всего страниц: {len(all_pages)}")
        print(f"Уникальных названий: {len([k for k in title_counts.keys() if k])}")
        print(f"Уникальных Event ID: {len([k for k in event_id_counts.keys() if k])}")
        print(f"Страниц с пустыми Event ID: {len(empty_event_id_pages)}")
        print(f"Дубликатов по названию: {len(title_duplicates)}")
        print(f"Дубликатов по Event ID: {len(event_duplicates)}")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке дубликатов в Notion: {e}")
        return False
    
    return True

if __name__ == "__main__":
    check_notion_api_duplicates()
