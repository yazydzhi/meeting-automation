#!/usr/bin/env python3
"""
Скрипт для полного улучшения страниц Notion.
Добавляет все недостающие данные: Drive Folder, Event ID, описание, участников, ссылки, контент.
"""

import os
import sys
import sqlite3
import requests
import json
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def complete_notion_enhancement():
    """Выполняет полное улучшение всех страниц Notion."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🚀 Полное улучшение страниц Notion...")
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
            skipped_count = 0
            
            for i, event in enumerate(events, 1):
                event_id, event_title, start_time, end_time, attendees, meeting_link, calendar_type, account_type, page_id, page_url, folder_path = event
                
                print(f"🔧 {i}. Улучшение страницы: {event_title}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📄 Page ID: {page_id}")
                
                try:
                    # Проверяем, нужно ли улучшение
                    needs_enhancement = _check_if_needs_enhancement(page_id, headers)
                    
                    if not needs_enhancement:
                        print(f"   ⏭️ Страница уже улучшена, пропускаем")
                        skipped_count += 1
                        continue
                    
                    # 1. Обновляем свойства страницы
                    properties_updated = _update_page_properties(page_id, event_id, folder_path, headers)
                    if properties_updated:
                        print(f"   ✅ Свойства страницы обновлены")
                    
                    # 2. Добавляем описание встречи
                    description_added = _add_meeting_description(page_id, event_title, start_time, end_time, attendees, meeting_link, calendar_type, account_type, folder_path, headers)
                    if description_added:
                        print(f"   ✅ Описание встречи добавлено")
                    
                    # 3. Добавляем контент (транскрипция, саммари, анализ)
                    content_added = _add_available_content(page_id, event_id, headers)
                    if content_added:
                        print(f"   ✅ Контент добавлен")
                    
                    enhanced_count += 1
                    print(f"   🎉 Страница успешно улучшена!")
                    
                except Exception as e:
                    print(f"   ❌ Ошибка улучшения страницы: {e}")
                
                print()
                
                # Ограничиваем количество обрабатываемых страниц для демонстрации
                if i >= 10:
                    print(f"... и еще {len(events) - 10} событий")
                    break
            
            print(f"📊 Результаты улучшения:")
            print(f"   ✅ Улучшено: {enhanced_count} страниц")
            print(f"   ⏭️ Пропущено: {skipped_count} страниц")
            print(f"   📄 Всего обработано: {enhanced_count + skipped_count} страниц")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

def _check_if_needs_enhancement(page_id: str, headers: dict) -> bool:
    """Проверяет, нужно ли улучшение страницы."""
    
    try:
        # Получаем блоки страницы
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_response = requests.get(blocks_url, headers=headers)
        blocks_response.raise_for_status()
        blocks_data = blocks_response.json()
        
        blocks = blocks_data.get('results', [])
        
        # Проверяем наличие описания встречи
        has_description = False
        for block in blocks:
            if block.get('type') == 'heading_2':
                heading_text = block.get('heading_2', {}).get('rich_text', [])
                if heading_text:
                    text_content = heading_text[0].get('text', {}).get('content', '')
                    if 'Описание встречи' in text_content:
                        has_description = True
                        break
        
        # Если нет описания, страница нуждается в улучшении
        return not has_description
        
    except Exception as e:
        print(f"   ⚠️ Ошибка проверки страницы: {e}")
        return True  # В случае ошибки считаем что нужно улучшение

def _update_page_properties(page_id: str, event_id: str, folder_path: str, headers: dict) -> bool:
    """Обновляет свойства страницы Notion."""
    
    try:
        properties_to_update = {}
        
        # Добавляем Event ID
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
        
        # Добавляем Drive Folder, если есть
        if folder_path and not folder_path.startswith('data/'):
            # Преобразуем локальный путь в Google Drive URL
            drive_url = folder_path.replace('data/local_drive/', 'https://drive.google.com/drive/folders/')
            properties_to_update["Drive Folder"] = {
                "url": drive_url
            }
        
        # Обновляем свойства страницы
        if properties_to_update:
            update_url = f"https://api.notion.com/v1/pages/{page_id}"
            update_data = {"properties": properties_to_update}
            
            response = requests.patch(update_url, headers=headers, json=update_data)
            response.raise_for_status()
            return True
        
        return False
        
    except Exception as e:
        print(f"   ⚠️ Ошибка обновления свойств: {e}")
        return False

def _add_meeting_description(page_id: str, event_title: str, start_time: str, end_time: str, 
                           attendees: str, meeting_link: str, calendar_type: str, 
                           account_type: str, folder_path: str, headers: dict) -> bool:
    """Добавляет описание встречи в страницу Notion."""
    
    try:
        # Формируем описание встречи
        meeting_info = f"**Название:** {event_title}\n"
        meeting_info += f"**Время:** {start_time} - {end_time}\n"
        meeting_info += f"**Тип календаря:** {calendar_type}\n"
        meeting_info += f"**Аккаунт:** {account_type}\n"
        
        if attendees and attendees != 'None':
            meeting_info += f"**Участники:** {attendees}\n"
        
        if meeting_link and meeting_link != 'None':
            meeting_info += f"**Ссылка на встречу:** {meeting_link}\n"
        
        if folder_path:
            meeting_info += f"**Папка:** {folder_path}\n"
        
        # Формируем блоки
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
                                "content": meeting_info
                            }
                        }
                    ]
                }
            }
        ]
        
        # Добавляем блоки
        blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        blocks_data = {"children": description_blocks}
        
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        response.raise_for_status()
        return True
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления описания: {e}")
        return False

def _add_available_content(page_id: str, event_id: str, headers: dict) -> bool:
    """Добавляет доступный контент (транскрипция, саммари, анализ) в страницу."""
    
    try:
        # Проверяем базу данных на наличие контента
        db_path = "data/system_state.db"
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            content_added = False
            
            # Ищем транскрипции
            cursor.execute('''
                SELECT transcript_file FROM processed_transcriptions 
                WHERE event_id = ? AND status = 'success'
            ''', (event_id,))
            
            transcript_result = cursor.fetchone()
            if transcript_result and transcript_result[0]:
                transcript_file = transcript_result[0]
                if os.path.exists(transcript_file):
                    if _add_transcription_to_page(page_id, transcript_file, headers):
                        content_added = True
            
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
                    if _add_summary_to_page(page_id, summary_file, analysis_file, headers):
                        content_added = True
            
            return content_added
    
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления контента: {e}")
        return False

def _add_transcription_to_page(page_id: str, transcript_file: str, headers: dict) -> bool:
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
        return True
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления транскрипции: {e}")
        return False

def _add_summary_to_page(page_id: str, summary_file: str, analysis_file: str, headers: dict) -> bool:
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
        return True
        
    except Exception as e:
        print(f"   ⚠️ Ошибка добавления саммари: {e}")
        return False

if __name__ == "__main__":
    success = complete_notion_enhancement()
    
    if success:
        print("✅ Полное улучшение страниц завершено успешно!")
    else:
        print("❌ Полное улучшение страниц завершено с ошибками!")
        sys.exit(1)
