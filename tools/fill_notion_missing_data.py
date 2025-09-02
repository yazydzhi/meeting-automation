#!/usr/bin/env python3
"""
Скрипт для заполнения недостающих данных в страницах Notion.
Заполняет даты, участников и ссылки на встречи на основе данных из SQLite.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def fill_notion_missing_data(dry_run=True):
    """Заполняет недостающие данные в страницах Notion."""
    
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
        
        print("🔧 Заполнение недостающих данных в страницах Notion...")
        print("=" * 70)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНОЕ ОБНОВЛЕНИЕ'}")
        print()
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из processed_events
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, 
                   attendees, meeting_link, calendar_type, account_type
            FROM processed_events
            ORDER BY event_start_time DESC
        """)
        
        db_events = cursor.fetchall()
        print(f"📊 Событий в SQLite: {len(db_events)}")
        
        # Создаем словарь для быстрого поиска по event_id
        db_events_dict = {}
        for event in db_events:
            event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type = event
            db_events_dict[event_id] = {
                'title': event_title,
                'start_time': event_start_time,
                'end_time': event_end_time,
                'attendees': attendees,
                'meeting_link': meeting_link,
                'calendar_type': calendar_type,
                'account_type': account_type
            }
        
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
            
            # Если есть Event ID и соответствующие данные в SQLite
            if event_id and event_id in db_events_dict:
                db_event = db_events_dict[event_id]
                
                # Получаем название страницы
                title = ""
                if 'Name' in properties:
                    title_prop = properties['Name']
                    if title_prop['type'] == 'title' and title_prop['title']:
                        title = title_prop['title'][0]['text']['content']
                
                # Проверяем, что нужно обновить
                updates_needed = {}
                
                # Проверяем дату
                notion_date = None
                if 'Date' in properties:
                    date_prop = properties['Date']
                    if date_prop['type'] == 'date' and date_prop['date']:
                        notion_date = date_prop['date']['start']
                
                if not notion_date and db_event['start_time']:
                    # Конвертируем ISO строку в дату для Notion
                    try:
                        start_dt = datetime.fromisoformat(db_event['start_time'].replace('Z', '+00:00'))
                        updates_needed['Date'] = {
                            "date": {
                                "start": start_dt.isoformat()
                            }
                        }
                    except:
                        pass
                
                # Проверяем участников
                notion_attendees = ""
                if 'Attendees' in properties:
                    attendees_prop = properties['Attendees']
                    if attendees_prop['type'] == 'rich_text' and attendees_prop['rich_text']:
                        notion_attendees = attendees_prop['rich_text'][0]['text']['content']
                
                if not notion_attendees and db_event['attendees']:
                    updates_needed['Attendees'] = {
                        "rich_text": [
                            {
                                "text": {
                                    "content": db_event['attendees']
                                }
                            }
                        ]
                    }
                
                # Проверяем ссылку на встречу
                notion_meeting_link = ""
                if 'Meeting Link' in properties:
                    meeting_link_prop = properties['Meeting Link']
                    if meeting_link_prop['type'] == 'url' and meeting_link_prop['url']:
                        notion_meeting_link = meeting_link_prop['url']
                
                if not notion_meeting_link and db_event['meeting_link']:
                    updates_needed['Meeting Link'] = {
                        "url": db_event['meeting_link']
                    }
                
                # Если есть обновления, добавляем в список
                if updates_needed:
                    pages_to_update.append({
                        'page_id': page_id,
                        'title': title,
                        'event_id': event_id,
                        'updates': updates_needed
                    })
        
        print(f"🔍 Найдено {len(pages_to_update)} страниц для обновления")
        print()
        
        if not pages_to_update:
            print("✅ Все страницы уже имеют все необходимые данные!")
            return True
        
        # Показываем что будет обновлено
        print("📋 Страницы для обновления:")
        print("-" * 70)
        for i, page in enumerate(pages_to_update[:10], 1):  # Показываем первые 10
            updates_list = ', '.join(page['updates'].keys())
            print(f"{i:2d}. {page['title'][:40]:<40} | {updates_list}")
        
        if len(pages_to_update) > 10:
            print(f"    ... и еще {len(pages_to_update) - 10} страниц")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Ничего не обновлено")
            print("💡 Для реального обновления запустите: python tools/fill_notion_missing_data.py --execute")
            return True
        
        # Реальное обновление
        print("🔧 Начинаю обновление страниц Notion...")
        updated_count = 0
        errors = []
        
        for i, page in enumerate(pages_to_update, 1):
            try:
                page_id = page['page_id']
                title = page['title']
                updates = page['updates']
                
                # Обновляем страницу
                url = f"https://api.notion.com/v1/pages/{page_id}"
                payload = {
                    "properties": updates
                }
                
                response = requests.patch(url, headers=headers, json=payload)
                response.raise_for_status()
                
                updated_count += 1
                updates_list = ', '.join(updates.keys())
                print(f"✅ {i:2d}/{len(pages_to_update)} Обновлена: {title[:40]} | {updates_list}")
                
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
        print(f"❌ Ошибка при заполнении недостающих данных: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального обновления добавьте --execute")
        print()
    
    success = fill_notion_missing_data(dry_run=dry_run)
    
    if success:
        print("\n✅ Заполнение недостающих данных завершено успешно!")
    else:
        print("\n❌ Заполнение завершено с ошибками!")
        sys.exit(1)
