#!/usr/bin/env python3
"""
Скрипт для проверки времени окончания встреч в Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def check_notion_end_time():
    """Проверяет время окончания встреч в Notion."""
    
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
        
        print("🕐 Проверка времени окончания встреч в Notion...")
        print("=" * 70)
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все события из SQLite
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, account_type
            FROM processed_events
            ORDER BY event_start_time DESC
        """)
        
        sqlite_events = cursor.fetchall()
        print(f"📊 Событий в SQLite: {len(sqlite_events)}")
        
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
        print()
        
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
        
        # Проверяем каждую страницу Notion
        missing_end_time = []
        mismatched_end_time = []
        correct_end_time = []
        
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
            
            # Получаем время окончания из Notion (из поля Date)
            notion_end_time = ""
            if 'Date' in properties:
                date_prop = properties['Date']
                if date_prop['type'] == 'date' and date_prop.get('date'):
                    notion_end_time = date_prop['date'].get('end', '')
            
            # Сравниваем с SQLite
            if event_id and event_id in sqlite_dict:
                sqlite_data = sqlite_dict[event_id]
                sqlite_end_time = sqlite_data['end_time']
                
                if not notion_end_time:
                    missing_end_time.append({
                        'title': title,
                        'event_id': event_id,
                        'sqlite_end_time': sqlite_end_time
                    })
                else:
                    # Нормализуем форматы времени для сравнения (убираем миллисекунды)
                    notion_normalized = notion_end_time.replace('.000', '') if '.000' in notion_end_time else notion_end_time
                    sqlite_normalized = sqlite_end_time.replace('.000', '') if '.000' in sqlite_end_time else sqlite_end_time
                    
                    if notion_normalized != sqlite_normalized:
                        mismatched_end_time.append({
                            'title': title,
                            'event_id': event_id,
                            'notion_end_time': notion_end_time,
                            'sqlite_end_time': sqlite_end_time
                        })
                    else:
                        correct_end_time.append({
                            'title': title,
                            'event_id': event_id,
                            'end_time': notion_end_time
                        })
        
        # Выводим результаты
        print("📋 Результаты проверки времени окончания:")
        print("-" * 70)
        
        if missing_end_time:
            print(f"❌ Отсутствует время окончания ({len(missing_end_time)} страниц):")
            for item in missing_end_time[:10]:  # Показываем первые 10
                print(f"  • {item['title'][:50]:<50} | SQLite: {item['sqlite_end_time']}")
            if len(missing_end_time) > 10:
                print(f"    ... и еще {len(missing_end_time) - 10} страниц")
            print()
        
        if mismatched_end_time:
            print(f"⚠️ Несовпадение времени окончания ({len(mismatched_end_time)} страниц):")
            for item in mismatched_end_time[:5]:  # Показываем первые 5
                print(f"  • {item['title'][:40]:<40}")
                print(f"    Notion: {item['notion_end_time']}")
                print(f"    SQLite: {item['sqlite_end_time']}")
            if len(mismatched_end_time) > 5:
                print(f"    ... и еще {len(mismatched_end_time) - 5} страниц")
            print()
        
        if correct_end_time:
            print(f"✅ Правильное время окончания ({len(correct_end_time)} страниц):")
            for item in correct_end_time[:5]:  # Показываем первые 5
                print(f"  • {item['title'][:50]:<50} | {item['end_time']}")
            if len(correct_end_time) > 5:
                print(f"    ... и еще {len(correct_end_time) - 5} страниц")
            print()
        
        # Общая статистика
        total_checked = len(missing_end_time) + len(mismatched_end_time) + len(correct_end_time)
        print("📊 Общая статистика:")
        print(f"  📄 Всего проверено страниц: {total_checked}")
        print(f"  ❌ Отсутствует время окончания: {len(missing_end_time)}")
        print(f"  ⚠️ Несовпадение времени: {len(mismatched_end_time)}")
        print(f"  ✅ Правильное время: {len(correct_end_time)}")
        
        if total_checked > 0:
            success_rate = (len(correct_end_time) / total_checked) * 100
            print(f"  📈 Процент правильности: {success_rate:.1f}%")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при проверке времени окончания в Notion: {e}")
        return False

if __name__ == "__main__":
    success = check_notion_end_time()
    
    if success:
        print("\n✅ Проверка времени окончания завершена успешно!")
    else:
        print("\n❌ Проверка завершена с ошибками!")
        sys.exit(1)
