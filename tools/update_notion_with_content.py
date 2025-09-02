#!/usr/bin/env python3
"""
Скрипт для обновления страниц Notion с транскрипциями, саммари и анализом.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv
from datetime import datetime

# Загружаем переменные окружения
load_dotenv()

def update_notion_with_content(dry_run=True):
    """Обновляет страницы Notion с транскрипциями, саммари и анализом."""
    
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
        
        print("📝 Обновление страниц Notion с контентом...")
        print("=" * 70)
        print(f"🔍 Режим: {'ТЕСТОВЫЙ (dry run)' if dry_run else 'РЕАЛЬНОЕ ОБНОВЛЕНИЕ'}")
        print()
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все записи с транскрипциями
        cursor.execute("""
            SELECT pt.event_id, pt.file_path, pt.transcript_file, pt.status,
                   pe.event_title, pe.account_type
            FROM processed_transcriptions pt
            JOIN processed_events pe ON pt.event_id = pe.event_id
            WHERE pt.status = 'success'
            ORDER BY pt.processed_at DESC
        """)
        
        transcriptions = cursor.fetchall()
        print(f"📊 Найдено транскрипций: {len(transcriptions)}")
        
        # Получаем все записи с саммари
        cursor.execute("""
            SELECT ps.event_id, ps.summary_file, ps.status,
                   pe.event_title, pe.account_type
            FROM processed_summaries ps
            JOIN processed_events pe ON ps.event_id = pe.event_id
            WHERE ps.status = 'success'
            ORDER BY ps.created_at DESC
        """)
        
        summaries = cursor.fetchall()
        print(f"📊 Найдено саммари: {len(summaries)}")
        
        # Создаем словари для быстрого поиска
        transcriptions_dict = {t[0]: t for t in transcriptions}
        summaries_dict = {s[0]: s for s in summaries}
        
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
            
            # Если есть Event ID и соответствующие данные
            if event_id:
                # Получаем название страницы
                title = ""
                if 'Name' in properties:
                    title_prop = properties['Name']
                    if title_prop['type'] == 'title' and title_prop['title']:
                        title = title_prop['title'][0]['text']['content']
                
                # Проверяем, есть ли транскрипция или саммари
                has_transcription = event_id in transcriptions_dict
                has_summary = event_id in summaries_dict
                
                if has_transcription or has_summary:
                    # Читаем содержимое файлов
                    content_updates = {}
                    
                    if has_transcription:
                        transcription_data = transcriptions_dict[event_id]
                        transcript_file = transcription_data[2]  # transcript_file
                        
                        if transcript_file and os.path.exists(transcript_file):
                            try:
                                with open(transcript_file, 'r', encoding='utf-8') as f:
                                    transcript_content = f.read()
                                
                                # Добавляем транскрипцию в контент страницы
                                content_updates['transcription'] = transcript_content
                            except Exception as e:
                                print(f"  ⚠️ Ошибка чтения транскрипции {transcript_file}: {e}")
                    
                    if has_summary:
                        summary_data = summaries_dict[event_id]
                        summary_file = summary_data[1]  # summary_file
                        
                        if summary_file and os.path.exists(summary_file):
                            try:
                                with open(summary_file, 'r', encoding='utf-8') as f:
                                    summary_content = f.read()
                                
                                # Добавляем саммари в контент страницы
                                content_updates['summary'] = summary_content
                            except Exception as e:
                                print(f"  ⚠️ Ошибка чтения саммари {summary_file}: {e}")
                    
                    if content_updates:
                        pages_to_update.append({
                            'page_id': page_id,
                            'title': title,
                            'event_id': event_id,
                            'content': content_updates
                        })
        
        print(f"🔍 Найдено {len(pages_to_update)} страниц для обновления контентом")
        print()
        
        if not pages_to_update:
            print("✅ Все страницы уже обновлены!")
            return True
        
        # Показываем что будет обновлено
        print("📋 Страницы для обновления:")
        print("-" * 70)
        for i, page in enumerate(pages_to_update[:10], 1):  # Показываем первые 10
            content_types = ', '.join(page['content'].keys())
            print(f"{i:2d}. {page['title'][:40]:<40} | {content_types}")
        
        if len(pages_to_update) > 10:
            print(f"    ... и еще {len(pages_to_update) - 10} страниц")
        
        print()
        
        if dry_run:
            print("🔍 ТЕСТОВЫЙ РЕЖИМ: Ничего не обновлено")
            print("💡 Для реального обновления запустите: python tools/update_notion_with_content.py --execute")
            return True
        
        # Реальное обновление
        print("📝 Начинаю обновление страниц Notion...")
        updated_count = 0
        errors = []
        
        for i, page in enumerate(pages_to_update, 1):
            try:
                page_id = page['page_id']
                title = page['title']
                content = page['content']
                
                # Формируем контент для добавления в страницу
                blocks_to_add = []
                
                if 'transcription' in content:
                    transcription_text = content['transcription']
                    
                    # Добавляем заголовок для транскрипции
                    blocks_to_add.append({
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
                    })
                    
                    # Добавляем транскрипцию
                    blocks_to_add.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": transcription_text
                                    }
                                }
                            ]
                        }
                    })
                
                if 'summary' in content:
                    summary_text = content['summary']
                    
                    # Добавляем заголовок для саммари
                    blocks_to_add.append({
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
                    
                    # Добавляем саммари
                    blocks_to_add.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": summary_text
                                    }
                                }
                            ]
                        }
                    })
                
                if blocks_to_add:
                    # Добавляем контент в страницу
                    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    payload = {
                        "children": blocks_to_add
                    }
                    
                    response = requests.patch(url, headers=headers, json=payload)
                    response.raise_for_status()
                    
                    updated_count += 1
                    content_types = ', '.join(content.keys())
                    print(f"✅ {i:2d}/{len(pages_to_update)} Обновлена: {title[:40]} | {content_types}")
                
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
        print(f"❌ Ошибка при обновлении страниц Notion: {e}")
        return False

if __name__ == "__main__":
    # Проверяем аргументы командной строки
    dry_run = "--execute" not in sys.argv
    
    if dry_run:
        print("🔍 Запуск в тестовом режиме (dry run)")
        print("💡 Для реального обновления добавьте --execute")
        print()
    
    success = update_notion_with_content(dry_run=dry_run)
    
    if success:
        print("\n✅ Обновление страниц Notion завершено успешно!")
    else:
        print("\n❌ Обновление завершено с ошибками!")
        sys.exit(1)
