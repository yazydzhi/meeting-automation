#!/usr/bin/env python3
"""
Скрипт для исправления времени окончания в страницах Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def fix_notion_end_time(dry_run=True):
    """Исправляет время окончания в страницах Notion."""
    
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
        
        print("🕐 Исправление времени окончания в страницах Notion...")
        print("=" * 70)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНОЕ ОБНОВЛЕНИЕ'}")
        print()
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все события из SQLite с временем окончания
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, account_type
            FROM processed_events
            WHERE event_end_time IS NOT NULL AND event_end_time != ''
            ORDER BY event_start_time DESC
        """)
        
        sqlite_events = cursor.fetchall()
        print(f"📊 Событий в SQLite с временем окончания: {len(sqlite_events)}")
        
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
        
        # Создаем словарь событий SQLite для быстрого поиска
        sqlite_dict = {}
        for event in sqlite_events:
            event_id, event_title, event_start_time, event_end_time, account_type = event
            sqlite_dict[event_id] = {
                'title': event_title,
                'start_time': event_start_time,
                'end_time': event_end_time,
                'account_type': account_type
            }
        
        # Находим страницы, которые нужно обновить
        pages_to_update = []
        
        for page in all_pages:
            page_id = page['id']
            properties = page['properties']
            
            # Получаем Event ID
            event_id = ""
            if 'Event ID' in properties:
                event_id_prop = properties['Event ID']
                if event_id_prop['type'] == 'rich_text' and event_id_prop['rich_text']:
                    event_id = event_id_prop['rich_text'][0]['text']['content']
            
            # Получаем название страницы
            title = ""
            if 'Name' in properties:
                title_prop = properties['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            # Получаем текущее поле Date
            current_date = None
            if 'Date' in properties:
                date_prop = properties['Date']
                if date_prop['type'] == 'date' and date_prop.get('date'):
                    current_date = date_prop['date']
            
            # Проверяем, нужно ли обновить время окончания
            if event_id and event_id in sqlite_dict:
                sqlite_data = sqlite_dict[event_id]
                sqlite_start_time = sqlite_data['start_time']
                sqlite_end_time = sqlite_data['end_time']
                
                # Проверяем, есть ли время окончания в текущем поле Date
                needs_update = False
                if not current_date or not current_date.get('end'):
                    needs_update = True
                elif current_date.get('end') != sqlite_end_time:
                    needs_update = True
                
                if needs_update:
                    pages_to_update.append({
                        'page_id': page_id,
                        'title': title,
                        'event_id': event_id,
                        'current_date': current_date,
                        'sqlite_start_time': sqlite_start_time,
                        'sqlite_end_time': sqlite_end_time
                    })
        
        print(f"🔍 Найдено {len(pages_to_update)} страниц для обновления времени окончания")
        print()
        
        if not pages_to_update:
            print("✅ Все страницы уже имеют правильное время окончания!")
            return True
        
        # Показываем что будет обновлено
        print("📋 Страницы для обновления:")
        print("-" * 70)
        for i, page in enumerate(pages_to_update[:10], 1):  # Показываем первые 10
            current_end = page['current_date'].get('end', 'отсутствует') if page['current_date'] else 'отсутствует'
            print(f"{i:2d}. {page['title'][:40]:<40} | Текущее: {current_end}")
            print(f"    Новое: {page['sqlite_end_time']}")
        
        if len(pages_to_update) > 10:
            print(f"    ... и еще {len(pages_to_update) - 10} страниц")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Ничего не обновлено")
            print("💡 Для реального обновления запустите: python tools/fix_notion_end_time.py --execute")
            return True
        
        # Реальное обновление
        print("📝 Начинаю обновление времени окончания в Notion...")
        updated_count = 0
        errors = []
        
        for i, page in enumerate(pages_to_update, 1):
            try:
                page_id = page['page_id']
                title = page['title']
                sqlite_start_time = page['sqlite_start_time']
                sqlite_end_time = page['sqlite_end_time']
                
                # Формируем новое поле Date с временем окончания
                new_date_property = {
                    "start": sqlite_start_time,
                    "end": sqlite_end_time
                }
                
                # Обновляем страницу
                url = f"https://api.notion.com/v1/pages/{page_id}"
                payload = {
                    "properties": {
                        "Date": {
                            "date": new_date_property
                        }
                    }
                }
                
                response = requests.patch(url, headers=headers, json=payload)
                response.raise_for_status()
                
                updated_count += 1
                print(f"✅ {i:2d}/{len(pages_to_update)} Обновлена: {title[:40]} | {sqlite_end_time}")
                
            except Exception as e:
                error_msg = f"Ошибка обновления {page['title']}: {e}"
                errors.append(error_msg)
                print(f"❌ {i:2d}/{len(pages_to_update)} {error_msg}")
        
        print()
        print("📊 Результаты обновления:")
        print(f"✅ Успешно обновлено: {updated_count}")
        print(f"❌ Ошибок: {len(errors)}")
        
        if errors:
            print("\n❌ Ошибки:")
            for error in errors:
                print(f"  - {error}")
        
        conn.close()
        return len(errors) == 0
        
    except Exception as e:
        print(f"❌ Ошибка при исправлении времени окончания в Notion: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального обновления добавьте --execute")
        print()
    
    success = fix_notion_end_time(dry_run=dry_run)
    
    if success:
        print("\n✅ Исправление времени окончания завершено успешно!")
    else:
        print("\n❌ Исправление завершено с ошибками!")
        sys.exit(1)
