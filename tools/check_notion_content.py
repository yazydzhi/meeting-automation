#!/usr/bin/env python3
"""
Скрипт для проверки контента в страницах Notion.
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

def check_notion_content():
    """Проверяет контент в страницах Notion."""
    
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
        
        print("📝 Проверка контента в страницах Notion...")
        print("=" * 60)
        
        # Получаем все страницы из Notion
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
        
        print(f"📊 Страниц в Notion: {len(all_pages)}")
        
        # Проверяем контент каждой страницы
        pages_with_content = 0
        pages_with_transcription = 0
        pages_with_summary = 0
        
        for page in all_pages:
            page_id = page['id']
            
            # Получаем название страницы
            title = ""
            if 'properties' in page and 'Name' in page['properties']:
                title_prop = page['properties']['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            # Получаем блоки страницы
            try:
                url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                blocks = data.get('results', [])
                
                # Проверяем наличие контента
                has_transcription = False
                has_summary = False
                
                for block in blocks:
                    if block['type'] == 'heading_2':
                        heading = block['heading_2']['rich_text']
                        if heading:
                            text = heading[0]['text']['content']
                            if 'Транскрипция' in text:
                                has_transcription = True
                            elif 'Саммари' in text or 'анализ' in text:
                                has_summary = True
                
                if has_transcription or has_summary:
                    pages_with_content += 1
                    if has_transcription:
                        pages_with_transcription += 1
                    if has_summary:
                        pages_with_summary += 1
                    
                    content_types = []
                    if has_transcription:
                        content_types.append("📝 Транскрипция")
                    if has_summary:
                        content_types.append("📊 Саммари")
                    
                    print(f"  ✅ {title[:50]:<50} | {', '.join(content_types)}")
                
            except Exception as e:
                print(f"  ❌ {title[:50]:<50} | Ошибка: {e}")
        
        print(f"\n📊 Статистика контента:")
        print(f"  📝 Страниц с транскрипциями: {pages_with_transcription}")
        print(f"  📊 Страниц с саммари: {pages_with_summary}")
        print(f"  📄 Страниц с любым контентом: {pages_with_content}")
        print(f"  📄 Всего страниц: {len(all_pages)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке контента Notion: {e}")
        return False

if __name__ == "__main__":
    success = check_notion_content()
    
    if success:
        print("\n✅ Проверка контента завершена успешно!")
    else:
        print("\n❌ Проверка завершена с ошибками!")
        sys.exit(1)
