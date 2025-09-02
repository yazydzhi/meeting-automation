#!/usr/bin/env python3
"""
Скрипт для проверки деталей событий в Notion: даты, участники, ссылки на встречи.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def check_notion_event_details():
    """Проверяет детали событий в Notion."""
    
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
        
        print("🔍 Проверка деталей событий в Notion...")
        print("=" * 80)
        
        # Подключаемся к SQLite базе данных для сравнения
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи из processed_events
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type, account_type
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
                'name': event_title,
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
        print()
        
        # Анализируем каждую страницу
        issues = {
            'missing_date': [],
            'missing_attendees': [],
            'missing_meeting_link': [],
            'date_mismatch': [],
            'attendees_mismatch': [],
            'meeting_link_mismatch': []
        }
        
        for page in all_pages:
            page_id = page['id']
            properties = page['properties']
            
            # Получаем Event ID
            event_id = ""
            if 'Event ID' in properties:
                event_id_prop = properties['Event ID']
                if event_id_prop['type'] == 'rich_text' and event_id_prop['rich_text']:
                    event_id = event_id_prop['rich_text'][0]['text']['content']
            
            # Получаем название
            title = ""
            if 'Name' in properties:
                title_prop = properties['Name']
                if title_prop['type'] == 'title' and title_prop['title']:
                    title = title_prop['title'][0]['text']['content']
            
            # Получаем дату
            notion_date = None
            if 'Date' in properties:
                date_prop = properties['Date']
                if date_prop['type'] == 'date' and date_prop['date']:
                    notion_date = date_prop['date']['start']
            
            # Получаем участников
            notion_attendees = ""
            if 'Attendees' in properties:
                attendees_prop = properties['Attendees']
                if attendees_prop['type'] == 'rich_text' and attendees_prop['rich_text']:
                    notion_attendees = attendees_prop['rich_text'][0]['text']['content']
            
            # Получаем ссылку на встречу
            notion_meeting_link = ""
            if 'Meeting Link' in properties:
                meeting_link_prop = properties['Meeting Link']
                if meeting_link_prop['type'] == 'url' and meeting_link_prop['url']:
                    notion_meeting_link = meeting_link_prop['url']
            
            # Проверяем наличие данных в SQLite
            if event_id in db_events_dict:
                db_event = db_events_dict[event_id]
                
                # Проверяем дату
                if not notion_date:
                    issues['missing_date'].append({
                        'page_id': page_id,
                        'title': title,
                        'event_id': event_id,
                        'db_date': db_event['start_time']
                    })
                else:
                    # Сравниваем даты (упрощенное сравнение)
                    db_date_str = db_event['start_time'][:10] if db_event['start_time'] else ""
                    notion_date_str = notion_date[:10] if notion_date else ""
                    if db_date_str != notion_date_str:
                        issues['date_mismatch'].append({
                            'page_id': page_id,
                            'title': title,
                            'event_id': event_id,
                            'db_date': db_event['start_time'],
                            'notion_date': notion_date
                        })
                
                # Проверяем участников
                if not notion_attendees:
                    issues['missing_attendees'].append({
                        'page_id': page_id,
                        'title': title,
                        'event_id': event_id,
                        'db_attendees': db_event['attendees']
                    })
                else:
                    # Сравниваем участников (упрощенное сравнение)
                    db_attendees = db_event['attendees'] or ""
                    if db_attendees.lower() != notion_attendees.lower():
                        issues['attendees_mismatch'].append({
                            'page_id': page_id,
                            'title': title,
                            'event_id': event_id,
                            'db_attendees': db_event['attendees'],
                            'notion_attendees': notion_attendees
                        })
                
                # Проверяем ссылку на встречу
                if not notion_meeting_link:
                    issues['missing_meeting_link'].append({
                        'page_id': page_id,
                        'title': title,
                        'event_id': event_id,
                        'db_meeting_link': db_event['meeting_link']
                    })
                else:
                    # Сравниваем ссылки
                    db_meeting_link = db_event['meeting_link'] or ""
                    if db_meeting_link != notion_meeting_link:
                        issues['meeting_link_mismatch'].append({
                            'page_id': page_id,
                            'title': title,
                            'event_id': event_id,
                            'db_meeting_link': db_event['meeting_link'],
                            'notion_meeting_link': notion_meeting_link
                        })
        
        # Выводим результаты
        print("📋 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
        print("=" * 80)
        
        # Отсутствующие даты
        if issues['missing_date']:
            print(f"\n❌ Отсутствующие даты ({len(issues['missing_date'])}):")
            print("-" * 50)
            for issue in issues['missing_date'][:5]:
                print(f"  📅 {issue['title'][:40]:<40} | {issue['db_date']}")
            if len(issues['missing_date']) > 5:
                print(f"  ... и еще {len(issues['missing_date']) - 5}")
        else:
            print("\n✅ Все страницы имеют даты")
        
        # Несоответствия дат
        if issues['date_mismatch']:
            print(f"\n⚠️ Несоответствия дат ({len(issues['date_mismatch'])}):")
            print("-" * 50)
            for issue in issues['date_mismatch'][:3]:
                print(f"  📅 {issue['title'][:30]:<30} | DB: {issue['db_date']} | Notion: {issue['notion_date']}")
            if len(issues['date_mismatch']) > 3:
                print(f"  ... и еще {len(issues['date_mismatch']) - 3}")
        else:
            print("\n✅ Все даты соответствуют")
        
        # Отсутствующие участники
        if issues['missing_attendees']:
            print(f"\n❌ Отсутствующие участники ({len(issues['missing_attendees'])}):")
            print("-" * 50)
            for issue in issues['missing_attendees'][:5]:
                print(f"  👥 {issue['title'][:40]:<40} | {issue['db_attendees']}")
            if len(issues['missing_attendees']) > 5:
                print(f"  ... и еще {len(issues['missing_attendees']) - 5}")
        else:
            print("\n✅ Все страницы имеют участников")
        
        # Несоответствия участников
        if issues['attendees_mismatch']:
            print(f"\n⚠️ Несоответствия участников ({len(issues['attendees_mismatch'])}):")
            print("-" * 50)
            for issue in issues['attendees_mismatch'][:3]:
                print(f"  👥 {issue['title'][:30]:<30} | DB: {issue['db_attendees']} | Notion: {issue['notion_attendees']}")
            if len(issues['attendees_mismatch']) > 3:
                print(f"  ... и еще {len(issues['attendees_mismatch']) - 3}")
        else:
            print("\n✅ Все участники соответствуют")
        
        # Отсутствующие ссылки на встречи
        if issues['missing_meeting_link']:
            print(f"\n❌ Отсутствующие ссылки на встречи ({len(issues['missing_meeting_link'])}):")
            print("-" * 50)
            for issue in issues['missing_meeting_link'][:5]:
                print(f"  🔗 {issue['title'][:40]:<40} | {issue['db_meeting_link']}")
            if len(issues['missing_meeting_link']) > 5:
                print(f"  ... и еще {len(issues['missing_meeting_link']) - 5}")
        else:
            print("\n✅ Все страницы имеют ссылки на встречи")
        
        # Несоответствия ссылок на встречи
        if issues['meeting_link_mismatch']:
            print(f"\n⚠️ Несоответствия ссылок на встречи ({len(issues['meeting_link_mismatch'])}):")
            print("-" * 50)
            for issue in issues['meeting_link_mismatch'][:3]:
                print(f"  🔗 {issue['title'][:30]:<30} | DB: {issue['db_meeting_link']} | Notion: {issue['notion_meeting_link']}")
            if len(issues['meeting_link_mismatch']) > 3:
                print(f"  ... и еще {len(issues['meeting_link_mismatch']) - 3}")
        else:
            print("\n✅ Все ссылки на встречи соответствуют")
        
        # Общая статистика
        print("\n📊 ОБЩАЯ СТАТИСТИКА:")
        print("-" * 30)
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        print(f"Всего проблем: {total_issues}")
        print(f"Отсутствующие даты: {len(issues['missing_date'])}")
        print(f"Несоответствия дат: {len(issues['date_mismatch'])}")
        print(f"Отсутствующие участники: {len(issues['missing_attendees'])}")
        print(f"Несоответствия участников: {len(issues['attendees_mismatch'])}")
        print(f"Отсутствующие ссылки: {len(issues['missing_meeting_link'])}")
        print(f"Несоответствия ссылок: {len(issues['meeting_link_mismatch'])}")
        
        conn.close()
        return total_issues == 0
        
    except Exception as e:
        print(f"❌ Ошибка при проверке деталей событий: {e}")
        return False

if __name__ == "__main__":
    success = check_notion_event_details()
    
    if success:
        print("\n✅ Все детали событий в порядке!")
    else:
        print("\n❌ Обнаружены проблемы с деталями событий!")
        sys.exit(1)
