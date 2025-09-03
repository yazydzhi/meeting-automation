#!/usr/bin/env python3
"""
Скрипт для проверки статуса контента в Notion страницах.
Проверяет, какие данные уже добавлены в страницы Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_notion_content_status():
    """Проверяет статус контента в Notion страницах."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🔍 Проверка статуса контента в Notion страницах...")
    print("=" * 80)
    
    # Проверяем переменные окружения
    notion_token = os.getenv('NOTION_TOKEN')
    notion_database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not notion_database_id:
        print("❌ Не найдены переменные окружения NOTION_TOKEN или NOTION_DATABASE_ID")
        return False
    
    # Подключаемся к базе данных
    db_path = "data/system_state.db"
    if not os.path.exists(db_path):
        print(f"❌ База данных не найдена: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Получаем все события с Notion страницами
            cursor.execute('''
                SELECT 
                    pe.event_id,
                    pe.event_title,
                    pe.event_start_time,
                    pe.event_end_time,
                    pe.attendees,
                    pe.meeting_link,
                    pe.calendar_type,
                    pe.account_type,
                    nss.page_id,
                    nss.page_url,
                    nss.sync_status
                FROM processed_events pe
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                WHERE nss.page_id IS NOT NULL
                ORDER BY pe.event_start_time DESC
            ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("❌ Не найдено событий с Notion страницами")
                return False
            
            print(f"📊 Найдено {len(events)} событий с Notion страницами")
            print()
            
            # Проверяем каждое событие
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28"
            }
            
            for i, event in enumerate(events, 1):
                event_id, event_title, start_time, end_time, attendees, meeting_link, calendar_type, account_type, page_id, page_url, sync_status = event
                
                print(f"📋 {i}. {event_title}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📅 Время: {start_time} - {end_time}")
                print(f"   👥 Участники: {attendees[:50] + '...' if attendees and len(attendees) > 50 else attendees}")
                print(f"   🔗 Ссылка: {meeting_link[:50] + '...' if meeting_link and len(meeting_link) > 50 else meeting_link}")
                print(f"   📄 Page ID: {page_id}")
                print(f"   🔄 Статус: {sync_status}")
                
                # Проверяем контент страницы
                try:
                    # Получаем свойства страницы
                    page_url = f"https://api.notion.com/v1/pages/{page_id}"
                    response = requests.get(page_url, headers=headers)
                    response.raise_for_status()
                    page_data = response.json()
                    
                    properties = page_data.get('properties', {})
                    
                    # Проверяем основные поля
                    print(f"   📝 Свойства страницы:")
                    
                    # Проверяем Date
                    date_prop = properties.get('Date', {})
                    if date_prop.get('date'):
                        date_value = date_prop['date']
                        print(f"      ✅ Date: {date_value.get('start', 'N/A')} - {date_value.get('end', 'N/A')}")
                    else:
                        print(f"      ❌ Date: отсутствует")
                    
                    # Проверяем Attendees
                    attendees_prop = properties.get('Attendees', {})
                    if attendees_prop.get('rich_text'):
                        attendees_text = attendees_prop['rich_text'][0].get('text', {}).get('content', '')
                        print(f"      ✅ Attendees: {attendees_text[:30] + '...' if len(attendees_text) > 30 else attendees_text}")
                    else:
                        print(f"      ❌ Attendees: отсутствует")
                    
                    # Проверяем Meeting Link
                    meeting_link_prop = properties.get('Meeting Link', {})
                    if meeting_link_prop.get('url'):
                        print(f"      ✅ Meeting Link: {meeting_link_prop['url'][:30] + '...' if len(meeting_link_prop['url']) > 30 else meeting_link_prop['url']}")
                    else:
                        print(f"      ❌ Meeting Link: отсутствует")
                    
                    # Проверяем Event ID
                    event_id_prop = properties.get('Event ID', {})
                    if event_id_prop.get('rich_text'):
                        event_id_text = event_id_prop['rich_text'][0].get('text', {}).get('content', '')
                        print(f"      ✅ Event ID: {event_id_text}")
                    else:
                        print(f"      ❌ Event ID: отсутствует")
                    
                    # Проверяем Drive Folder
                    drive_folder_prop = properties.get('Drive Folder', {})
                    if drive_folder_prop.get('url'):
                        print(f"      ✅ Drive Folder: {drive_folder_prop['url'][:30] + '...' if len(drive_folder_prop['url']) > 30 else drive_folder_prop['url']}")
                    else:
                        print(f"      ❌ Drive Folder: отсутствует")
                    
                    # Получаем блоки страницы для проверки контента
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_response = requests.get(blocks_url, headers=headers)
                    blocks_response.raise_for_status()
                    blocks_data = blocks_response.json()
                    
                    blocks = blocks_data.get('results', [])
                    
                    # Проверяем наличие контента
                    has_transcription = False
                    has_summary = False
                    has_analysis = False
                    
                    for block in blocks:
                        block_type = block.get('type', '')
                        if block_type == 'heading_2':
                            heading_text = block.get('heading_2', {}).get('rich_text', [])
                            if heading_text:
                                text_content = heading_text[0].get('text', {}).get('content', '')
                                if 'Транскрипция' in text_content:
                                    has_transcription = True
                                elif 'Саммари' in text_content:
                                    has_summary = True
                                elif 'анализ' in text_content.lower():
                                    has_analysis = True
                    
                    print(f"   📄 Контент страницы:")
                    print(f"      {'✅' if has_transcription else '❌'} Транскрипция")
                    print(f"      {'✅' if has_summary else '❌'} Саммари")
                    print(f"      {'✅' if has_analysis else '❌'} Анализ")
                    print(f"      📊 Всего блоков: {len(blocks)}")
                    
                except Exception as e:
                    print(f"      ❌ Ошибка проверки страницы: {e}")
                
                print()
                
                # Ограничиваем количество проверяемых страниц
                if i >= 10:
                    print(f"... и еще {len(events) - 10} событий")
                    break
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

if __name__ == "__main__":
    success = check_notion_content_status()
    
    if success:
        print("✅ Проверка завершена успешно!")
    else:
        print("❌ Проверка завершена с ошибками!")
        sys.exit(1)
