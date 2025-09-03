#!/usr/bin/env python3
"""
Скрипт для проверки синхронизации транскрипций, саммари и анализа между файловой системой, БД и Notion.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_transcription_sync_status():
    """Проверяет синхронизацию транскрипций, саммари и анализа."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("🔍 Проверка синхронизации транскрипций, саммари и анализа...")
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
                    nss.page_id
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
            
            # Настраиваем заголовки для Notion API
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28"
            }
            
            # Статистика
            total_events = len(events)
            events_with_transcriptions = 0
            events_with_summaries = 0
            events_with_notion_content = 0
            events_fully_synced = 0
            
            for i, event in enumerate(events, 1):
                event_id, event_title, start_time, page_id = event
                
                print(f"📋 {i}. {event_title}")
                print(f"   🆔 Event ID: {event_id}")
                print(f"   📅 Время: {start_time}")
                print(f"   📄 Page ID: {page_id}")
                
                # Проверяем транскрипции в БД
                cursor.execute('''
                    SELECT file_path, transcript_file, status 
                    FROM processed_transcriptions 
                    WHERE event_id = ?
                ''', (event_id,))
                
                transcriptions = cursor.fetchall()
                
                if transcriptions:
                    events_with_transcriptions += 1
                    print(f"   📝 Транскрипции в БД: {len(transcriptions)}")
                    
                    for trans in transcriptions:
                        file_path, transcript_file, status = trans
                        file_exists = os.path.exists(transcript_file) if transcript_file else False
                        print(f"      {'✅' if file_exists else '❌'} {os.path.basename(transcript_file)} ({status})")
                else:
                    print(f"   📝 Транскрипции в БД: ❌")
                
                # Проверяем саммари в БД
                cursor.execute('''
                    SELECT transcript_file, summary_file, analysis_file, status 
                    FROM processed_summaries 
                    WHERE event_id = ?
                ''', (event_id,))
                
                summaries = cursor.fetchall()
                
                if summaries:
                    events_with_summaries += 1
                    print(f"   📊 Саммари в БД: {len(summaries)}")
                    
                    for summary in summaries:
                        transcript_file, summary_file, analysis_file, status = summary
                        summary_exists = os.path.exists(summary_file) if summary_file else False
                        analysis_exists = os.path.exists(analysis_file) if analysis_file else False
                        print(f"      {'✅' if summary_exists else '❌'} Саммари: {os.path.basename(summary_file) if summary_file else 'N/A'}")
                        print(f"      {'✅' if analysis_exists else '❌'} Анализ: {os.path.basename(analysis_file) if analysis_file else 'N/A'}")
                else:
                    print(f"   📊 Саммари в БД: ❌")
                
                # Проверяем контент в Notion
                try:
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_response = requests.get(blocks_url, headers=headers)
                    blocks_response.raise_for_status()
                    blocks_data = blocks_response.json()
                    
                    blocks = blocks_data.get('results', [])
                    
                    has_transcription = False
                    has_summary = False
                    has_analysis = False
                    
                    for block in blocks:
                        if block.get('type') == 'heading_2':
                            heading_text = block.get('heading_2', {}).get('rich_text', [])
                            if heading_text:
                                text_content = heading_text[0].get('text', {}).get('content', '')
                                if 'Транскрипция' in text_content:
                                    has_transcription = True
                                elif 'Саммари' in text_content:
                                    has_summary = True
                                elif 'анализ' in text_content.lower():
                                    has_analysis = True
                    
                    if has_transcription or has_summary or has_analysis:
                        events_with_notion_content += 1
                        print(f"   📄 Контент в Notion:")
                        print(f"      {'✅' if has_transcription else '❌'} Транскрипция")
                        print(f"      {'✅' if has_summary else '❌'} Саммари")
                        print(f"      {'✅' if has_analysis else '❌'} Анализ")
                    else:
                        print(f"   📄 Контент в Notion: ❌")
                    
                    # Проверяем полную синхронизацию
                    if (transcriptions and summaries and 
                        has_transcription and has_summary):
                        events_fully_synced += 1
                        print(f"   🎉 Полная синхронизация: ✅")
                    else:
                        print(f"   🎉 Полная синхронизация: ❌")
                
                except Exception as e:
                    print(f"   ❌ Ошибка проверки Notion: {e}")
                
                print()
                
                # Ограничиваем количество проверяемых событий
                if i >= 10:
                    print(f"... и еще {len(events) - 10} событий")
                    break
            
            # Итоговая статистика
            print("📊 ИТОГОВАЯ СТАТИСТИКА:")
            print("=" * 50)
            print(f"📄 Всего событий: {total_events}")
            print(f"📝 Событий с транскрипциями: {events_with_transcriptions}")
            print(f"📊 Событий с саммари: {events_with_summaries}")
            print(f"📄 Событий с контентом в Notion: {events_with_notion_content}")
            print(f"🎉 Полностью синхронизированных: {events_fully_synced}")
            print()
            
            # Процент синхронизации
            if total_events > 0:
                transcription_percent = (events_with_transcriptions / total_events) * 100
                summary_percent = (events_with_summaries / total_events) * 100
                notion_percent = (events_with_notion_content / total_events) * 100
                full_sync_percent = (events_fully_synced / total_events) * 100
                
                print("📈 ПРОЦЕНТЫ СИНХРОНИЗАЦИИ:")
                print(f"📝 Транскрипции: {transcription_percent:.1f}%")
                print(f"📊 Саммари: {summary_percent:.1f}%")
                print(f"📄 Notion контент: {notion_percent:.1f}%")
                print(f"🎉 Полная синхронизация: {full_sync_percent:.1f}%")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

if __name__ == "__main__":
    success = check_transcription_sync_status()
    
    if success:
        print("✅ Проверка синхронизации завершена успешно!")
    else:
        print("❌ Проверка синхронизации завершена с ошибками!")
        sys.exit(1)
