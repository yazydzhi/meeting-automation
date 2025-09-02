#!/usr/bin/env python3
"""
Скрипт для очистки дубликатов в Notion.
"""

import os
import sys
import requests
from collections import defaultdict
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def cleanup_notion_duplicates(dry_run=True):
    """Очищает дубликаты в Notion."""
    
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
        
        print("🧹 Очистка дубликатов в Notion...")
        print("=" * 60)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНОЕ УДАЛЕНИЕ'}")
        print()
        
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
        
        # Группируем страницы по названию
        title_groups = defaultdict(list)
        
        for page in all_pages:
            # Получаем название страницы
            title = ""
            if 'properties' in page and 'Name' in page['properties']:
                title_prop = page['properties']['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            if title:  # Только страницы с названием
                title_groups[title].append({
                    'page_id': page['id'],
                    'title': title,
                    'created_time': page['created_time'],
                    'page': page
                })
        
        # Находим дубликаты
        duplicates_to_remove = []
        total_duplicates = 0
        
        for title, pages in title_groups.items():
            if len(pages) > 1:
                # Сортируем по дате создания (оставляем самую новую)
                pages.sort(key=lambda x: x['created_time'], reverse=True)
                
                # Помечаем все кроме первой (самой новой) для удаления
                for page in pages[1:]:
                    duplicates_to_remove.append({
                        'page_id': page['page_id'],
                        'title': title,
                        'created_time': page['created_time'],
                        'reason': f"Дубликат '{title}' (оставляем самую новую: {pages[0]['created_time']})"
                    })
                    total_duplicates += 1
        
        print(f"🔍 Найдено {total_duplicates} дубликатов для удаления")
        print()
        
        if not duplicates_to_remove:
            print("✅ Дубликатов не найдено!")
            return True
        
        # Показываем что будет удалено
        print("📋 Страницы для удаления:")
        print("-" * 40)
        for i, duplicate in enumerate(duplicates_to_remove[:10], 1):  # Показываем первые 10
            print(f"{i:2d}. {duplicate['title'][:50]:<50} | {duplicate['created_time'][:19]}")
        
        if len(duplicates_to_remove) > 10:
            print(f"    ... и еще {len(duplicates_to_remove) - 10} страниц")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Ничего не удалено")
            print("💡 Для реального удаления запустите: python tools/cleanup_notion_duplicates.py --execute")
            return True
        
        # Реальное удаление
        print("🗑️ Начинаю удаление дубликатов...")
        deleted_count = 0
        errors = []
        
        for i, duplicate in enumerate(duplicates_to_remove, 1):
            try:
                page_id = duplicate['page_id']
                title = duplicate['title']
                
                # Удаляем страницу
                url = f"https://api.notion.com/v1/pages/{page_id}"
                response = requests.patch(url, headers=headers, json={"archived": True})
                response.raise_for_status()
                
                deleted_count += 1
                print(f"✅ {i:2d}/{len(duplicates_to_remove)} Удалена: {title[:50]}")
                
            except Exception as e:
                error_msg = f"Ошибка удаления {duplicate['title']}: {e}"
                errors.append(error_msg)
                print(f"❌ {i:2d}/{len(duplicates_to_remove)} {error_msg}")
        
        print()
        print("📊 Результаты удаления:")
        print(f"✅ Успешно удалено: {deleted_count}")
        print(f"❌ Ошибок: {len(errors)}")
        
        if errors:
            print("\n❌ Ошибки:")
            for error in errors:
                print(f"  - {error}")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Ошибка при очистке дубликатов: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального удаления добавьте --execute")
        print()
    
    success = cleanup_notion_duplicates(dry_run=dry_run)
    
    if success:
        print("\n✅ Очистка завершена успешно!")
    else:
        print("\n❌ Очистка завершена с ошибками!")
        sys.exit(1)
