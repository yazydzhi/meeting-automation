#!/usr/bin/env python3
"""
Скрипт для улучшения страниц Notion.
Добавляет недостающие данные: Drive Folder, описание события, и контент.
"""

import os
import sys
import sqlite3
import requests
import json
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def enhance_notion_pages():
    """Улучшает страницы Notion, добавляя недостающие данные."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🔧 Улучшение страниц Notion...")
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
                    fcs.folder_path
                FROM processed_events pe
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                LEFT JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id
                WHERE nss.page_id IS NOT NULL
                ORDER BY pe.event_start_time DESC
                LIMIT 10
            ''')
            
            events = cursor.fetchall()
            
            if not events:
                print("❌ Не найдено событий с Notion страницами")
                return False
            
            print(f"📊 Найдено {len(events)} событий для улучшения")
            print()
            
            # Настраиваем заголовки для Notion API
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28",
                "Content-Type": "application/json"
            }
            
            enhanced_count = 0
            
            for i, event in enumerate(events, 1):
                event_id, event_title, start_time, end_time, attendees, meeting_link, calendar_type, account_type, page_id, page_url, folder_path = event
                
                print(f"🔧 {i}. Улучшение страницы: {event_title}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📄 Page ID: {page_id}")
                
                try:
                    # 1. Обновляем свойства страницы
                    properties_to_update = {}
                    
                    # Добавляем Drive Folder, если есть
                    if folder_path and not folder_path.startswith('data/'):
                        # Преобразуем локальный путь в Google Drive URL
                        drive_url = folder_path.replace('data/local_drive/', 'https://drive.google.com/drive/folders/')
                        properties_to_update["Drive Folder"] = {
                            "url": drive_url
                        }
                        print(f"   📁 Добавляем Drive Folder: {drive_url[:50]}...")
                    
                    # Добавляем Event ID, если отсутствует
                    properties_to_update["Event ID"] = {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": event_id
                                }
                            }
                        ]
                    }
                    print(f"   🆔 Добавляем Event ID: {event_id}")
                    
                    # Обновляем свойства страницы
                    if properties_to_update:
                        update_url = f"https://api.notion.com/v1/pages/{page_id}"
                        update_data = {"properties": properties_to_update}
                        
                        response = requests.patch(update_url, headers=headers, json=update_data)
                        response.raise_for_status()
                        print(f"   ✅ Свойства страницы обновлены")
                    
                    # 2. Добавляем описание события
                    description_blocks = []
                    
                    # Заголовок для описания
                    description_blocks.append({
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
                    })
                    
                    # Информация о встрече
                    meeting_info = f"**Название:** {event_title}\n"
                    meeting_info += f"**Время:** {start_time} - {end_time}\n"
                    meeting_info += f"**Тип календаря:** {calendar_type}\n"
                    meeting_info += f"**Аккаунт:** {account_type}\n"
                    
                    if attendees:
                        meeting_info += f"**Участники:** {attendees}\n"
                    
                    if meeting_link:
                        meeting_info += f"**Ссылка на встречу:** {meeting_link}\n"
                    
                    if folder_path:
                        meeting_info += f"**Папка:** {folder_path}\n"
                    
                    description_blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": meeting_info
                                    }
                                }
                            ]
                        }
                    })
                    
                    # Добавляем блоки описания
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_data = {"children": description_blocks}
                    
                    response = requests.patch(blocks_url, headers=headers, json=blocks_data)
                    response.raise_for_status()
                    print(f"   ✅ Описание встречи добавлено")
                    
                    # 3. Проверяем и добавляем контент (транскрипция, саммари, анализ)
                    _add_content_if_available(page_id, event_id, headers)
                    
                    enhanced_count += 1
                    print(f"   🎉 Страница успешно улучшена!")
                    
                except Exception as e:
                    print(f"   ❌ Ошибка улучшения страницы: {e}")
                
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

def _add_content_if_available(page_id: str, event_id: str, headers: dict):
    """Добавляет контент в страницу Notion, если он доступен."""
    
    try:
        # Проверяем базу данных на наличие контента
        db_path = "data/system_state.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Ищем транскрипции
            cursor.execute('''
                SELECT transcript_file FROM processed_transcriptions 
                WHERE event_id = ? AND status = 'success'
            ''', (event_id,))
            
            transcript_result = cursor.fetchone()
            if transcript_result and transcript_result[0]:
                transcript_file = transcript_result[0]
                if os.path.exists(transcript_file):
                    _add_transcription_to_page(page_id, transcript_file, headers)
            
            # Ищем саммари
            cursor.execute('''
                SELECT summary_file, analysis_file FROM processed_summaries 
                WHERE event_id = ? AND status = 'success'
            ''', (event_id,))
            
            summary_result = cursor.fetchone()
            if summary_result and summary_result[0]:
                summary_file = summary_result[0]
                analysis_file = summary_result[1] if len(summary_result) > 1 else None
                
                if os.path.exists(summary_file):
                    _add_summary_to_page(page_id, summary_file, analysis_file, headers)
    
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления контента: {e}")

def _add_transcription_to_page(page_id: str, transcript_file: str, headers: dict):
    """Добавляет транскрипцию в страницу Notion."""
    
    try:
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_content = f.read()
        
        blocks = [
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📝 Транскрипция встречи"
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
                                "content": transcript_content
                            }
                        }
                    ]
                }
            }
        ]
        
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_data = {"children": blocks}
        
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        response.raise_for_status()
        print(f"   ✅ Транскрипция добавлена")
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления транскрипции: {e}")

def _add_summary_to_page(page_id: str, summary_file: str, analysis_file: str, headers: dict):
    """Добавляет саммари и анализ в страницу Notion."""
    
    try:
        blocks = []
        
        # Заголовок для саммари
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📊 Саммари и анализ"
                        }
                    }
                ]
            }
        })
        
        # Саммари
        with open(summary_file, 'r', encoding='utf-8') as f:
            summary_content = f.read()
        
        blocks.append({
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": summary_content
                        }
                    }
                ]
            }
        })
        
        # Анализ (если есть)
        if analysis_file and os.path.exists(analysis_file):
            blocks.append({
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🔍 Детальный анализ"
                            }
                        }
                    ]
                }
            })
            
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_content = f.read()
            
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": analysis_content
                            }
                        }
                    ]
                }
            })
        
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_data = {"children": blocks}
        
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        response.raise_for_status()
        print(f"   ✅ Саммари и анализ добавлены")
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления саммари: {e}")

if __name__ == "__main__":
    success = enhance_notion_pages()
    
    if success:
        print("✅ Улучшение страниц завершено успешно!")
    else:
        print("❌ Улучшение страниц завершено с ошибками!")
        sys.exit(1)
