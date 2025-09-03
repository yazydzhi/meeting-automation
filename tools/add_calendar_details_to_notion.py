#!/usr/bin/env python3
"""
Скрипт для добавления деталей календаря в страницы Notion.
Добавляет описание события, участников, ссылки на встречи из календаря.
"""

import os
import sys
import sqlite3
import requests
import json
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def add_calendar_details_to_notion():
    """Добавляет детали календаря в страницы Notion."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("📅 Добавление деталей календаря в страницы Notion...")
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
            
            # Получаем события с недостающими данными
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
                    nss.page_url
                FROM processed_events pe
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                WHERE nss.page_id IS NOT NULL
                AND (
                    pe.attendees IS NULL OR pe.attendees = '' OR pe.attendees = 'None'
                    OR pe.meeting_link IS NULL OR pe.meeting_link = '' OR pe.meeting_link = 'None'
                )
                ORDER BY pe.event_start_time DESC
                LIMIT 10
            ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("✅ Все события уже имеют полные данные")
                return True
            
            print(f"📊 Найдено {len(events)} событий с недостающими данными")
            print()
            
            # Настраиваем заголовки для Notion API
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            enhanced_count = 0
            
            for i, event in enumerate(events, 1):
                event_id, event_title, start_time, end_time, attendees, meeting_link, calendar_type, account_type, page_id, page_url = event
                
                print(f"📅 {i}. Добавление деталей календаря: {event_title}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📄 Page ID: {page_id}")
                
                try:
                    # Получаем свежие данные из календаря
                    calendar_data = _get_calendar_event_data(event_id, account_type, calendar_type)
                    
                    if not calendar_data:
                        print(f"   ⚠️ Не удалось получить данные из календаря")
                        continue
                    
                    # Обновляем свойства страницы
                    properties_to_update = {}
                    
                    # Добавляем участников, если есть
                    if calendar_data.get('attendees') and not attendees:
                        attendees_list = calendar_data['attendees']
                        if isinstance(attendees_list, list) and attendees_list:
                            attendees_text = ", ".join(attendees_list[:10])  # Ограничиваем количество
                            properties_to_update["Attendees"] = {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": attendees_text
                                        }
                                    }
                                ]
                            }
                            print(f"   👥 Добавляем участников: {len(attendees_list)} человек")
                    
                    # Добавляем ссылку на встречу, если есть
                    if calendar_data.get('meeting_link') and not meeting_link:
                        properties_to_update["Meeting Link"] = {
                            "url": calendar_data['meeting_link']
                        }
                        print(f"   🔗 Добавляем ссылку на встречу: {calendar_data['meeting_link'][:50]}...")
                    
                    # Обновляем свойства страницы
                    if properties_to_update:
                        update_url = f"https://api.notion.com/v1/pages/{page_id}"
                        update_data = {"properties": properties_to_update}
                        
                        response = requests.patch(update_url, headers=headers, json=update_data)
                        response.raise_for_status()
                        print(f"   ✅ Свойства страницы обновлены")
                        
                        # Обновляем данные в базе данных
                        _update_event_data_in_db(event_id, calendar_data)
                    
                    # Добавляем описание события, если есть
                    if calendar_data.get('description'):
                        _add_event_description_to_page(page_id, calendar_data, headers)
                        print(f"   ✅ Описание события добавлено")
                    
                    enhanced_count += 1
                    print(f"   🎉 Детали календаря успешно добавлены!")
                    
                except Exception as e:
                    print(f"   ❌ Ошибка добавления деталей: {e}")
                
                print()
                
                # Ограничиваем количество обрабатываемых страниц
                if i >= 5:
                    print(f"... и еще {len(events) - 5} событий")
                    break
            
            print(f"✅ Улучшено {enhanced_count} из {min(len(events), 5)} страниц")
            return True
            
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

def _get_calendar_event_data(event_id: str, account_type: str, calendar_type: str) -> dict:
    """Получает данные события из календаря."""
    
    try:
        # Импортируем необходимые модули
        from src.config_manager import ConfigManager
        from src.handlers.calendar_handler import CalendarHandler
        
        # Создаем конфигурацию
        config_manager = ConfigManager()
        
        # Создаем обработчик календаря
        calendar_handler = CalendarHandler(config_manager)
        
        # Получаем события из календаря
        events = calendar_handler.get_calendar_events(account_type)
        
        # Ищем нужное событие
        for event in events:
            if event.get('id') == event_id:
                return event
        
        return {}
        
    except Exception as e:
        print(f"   ⚠️ Ошибка получения данных календаря: {e}")
        return {}

def _update_event_data_in_db(event_id: str, calendar_data: dict):
    """Обновляет данные события в базе данных."""
    
    try:
        db_path = "data/system_state.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Обновляем данные события
            cursor.execute('''
                UPDATE processed_events 
                SET attendees = ?, meeting_link = ?
                WHERE event_id = ?
            ''', (
                json.dumps(calendar_data.get('attendees', [])),
                calendar_data.get('meeting_link', ''),
                event_id
            ))
            
            conn.commit()
            
    except Exception as e:
        print(f"   ⚠️ Ошибка обновления данных в БД: {e}")

def _add_event_description_to_page(page_id: str, calendar_data: dict, headers: dict):
    """Добавляет описание события в страницу Notion."""
    
    try:
        description = calendar_data.get('description', '')
        if not description:
            return
        
        # Проверяем, не добавлено ли уже описание
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=headers)
        blocks_response.raise_for_status()
        blocks_data = blocks_response.json()
        
        blocks = blocks_data.get('results', [])
        
        # Проверяем, есть ли уже описание
        has_description = False
        for block in blocks:
            if block.get('type') == 'heading_2':
                heading_text = block.get('heading_2', {}).get('rich_text', [])
                if heading_text:
                    text_content = heading_text[0].get('text', {}).get('content', '')
                    if 'Описание встречи' in text_content:
                        has_description = True
                        break
        
        if has_description:
            return
        
        # Добавляем описание
        description_blocks = [
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📋 Описание встречи"
                            }
                        }
                    ]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": description
                            }
                        }
                    ]
                }
            }
        ]
        
        blocks_data = {"children": description_blocks}
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        response.raise_for_status()
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления описания: {e}")

if __name__ == "__main__":
    success = add_calendar_details_to_notion()
    
    if success:
        print("✅ Добавление деталей календаря завершено успешно!")
    else:
        print("❌ Добавление деталей календаря завершено с ошибками!")
        sys.exit(1)
