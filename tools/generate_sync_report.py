#!/usr/bin/env python3
"""
Скрипт для генерации отчета о синхронизации транскрипций, саммари и анализа.
"""

import os
import sys
import sqlite3
import requests
from dotenv import load_dotenv

# Добавляем путь к модулям проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def generate_sync_report():
    """Генерирует отчет о синхронизации."""
    
    # Загружаем переменные окружения
    load_dotenv()
    
    print("📊 ОТЧЕТ О СИНХРОНИЗАЦИИ ТРАНСКРИПЦИЙ, САММАРИ И АНАЛИЗА")
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
            
            # Общая статистика
            print("📈 ОБЩАЯ СТАТИСТИКА:")
            print("-" * 50)
            
            # События
            cursor.execute('SELECT COUNT(*) FROM processed_events')
            total_events = cursor.fetchone()[0]
            print(f"📄 Всего событий: {total_events}")
            
            # События с Notion страницами
            cursor.execute('''
                SELECT COUNT(*) FROM processed_events pe
                LEFT JOIN notion_sync_status nss ON pe.event_id = nss.event_id
                WHERE nss.page_id IS NOT NULL
            ''')
            events_with_notion = cursor.fetchone()[0]
            print(f"📄 Событий с Notion страницами: {events_with_notion}")
            
            # Транскрипции
            cursor.execute('SELECT COUNT(*) FROM processed_transcriptions')
            total_transcriptions = cursor.fetchone()[0]
            print(f"📝 Всего транскрипций: {total_transcriptions}")
            
            # Саммари
            cursor.execute('SELECT COUNT(*) FROM processed_summaries')
            total_summaries = cursor.fetchone()[0]
            print(f"📊 Всего саммари: {total_summaries}")
            
            # Медиа файлы
            cursor.execute('SELECT COUNT(*) FROM processed_media')
            total_media = cursor.fetchone()[0]
            print(f"🎥 Всего медиа файлов: {total_media}")
            
            print()
            
            # События с транскрипциями
            print("📝 СОБЫТИЯ С ТРАНСКРИПЦИЯМИ:")
            print("-" * 50)
            
            cursor.execute('''
                SELECT 
                    pe.event_id,
                    pe.event_title,
                    pe.event_start_time,
                    COUNT(pt.transcript_file) as transcript_count
                FROM processed_events pe
                LEFT JOIN processed_transcriptions pt ON pe.event_id = pt.event_id
                WHERE pt.event_id IS NOT NULL
                GROUP BY pe.event_id, pe.event_title, pe.event_start_time
                ORDER BY pe.event_start_time DESC
            ''')
            
            events_with_transcriptions = cursor.fetchall()
            
            if events_with_transcriptions:
                for event in events_with_transcriptions:
                    event_id, event_title, start_time, transcript_count = event
                    print(f"✅ {event_title}")
                    print(f"   📅 {start_time}")
                    print(f"   🆔 {event_id}")
                    print(f"   📝 Транскрипций: {transcript_count}")
                    print()
            else:
                print("❌ Событий с транскрипциями не найдено")
            
            # События с саммари
            print("📊 СОБЫТИЯ С САММАРИ:")
            print("-" * 50)
            
            cursor.execute('''
                SELECT 
                    pe.event_id,
                    pe.event_title,
                    pe.event_start_time,
                    COUNT(ps.summary_file) as summary_count
                FROM processed_events pe
                LEFT JOIN processed_summaries ps ON pe.event_id = ps.event_id
                WHERE ps.event_id IS NOT NULL
                GROUP BY pe.event_id, pe.event_title, pe.event_start_time
                ORDER BY pe.event_start_time DESC
            ''')
            
            events_with_summaries = cursor.fetchall()
            
            if events_with_summaries:
                for event in events_with_summaries:
                    event_id, event_title, start_time, summary_count = event
                    print(f"✅ {event_title}")
                    print(f"   📅 {start_time}")
                    print(f"   🆔 {event_id}")
                    print(f"   📊 Саммари: {summary_count}")
                    print()
            else:
                print("❌ Событий с саммари не найдено")
            
            # Проверяем контент в Notion
            print("📄 КОНТЕНТ В NOTION:")
            print("-" * 50)
            
            # Настраиваем заголовки для Notion API
            headers = {
                "Authorization": f"Bearer {notion_token}",
                "Notion-Version": "2022-06-28"
            }
            
            # Получаем события с Notion страницами
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
            
            notion_events = cursor.fetchall()
            
            events_with_notion_content = 0
            events_with_transcription_content = 0
            events_with_summary_content = 0
            
            for event in notion_events:
                event_id, event_title, start_time, page_id = event
                
                try:
                    # Получаем блоки страницы
                    blocks_url = f"https://api.notion.com/v1/blocks/{page_id}/children"
                    blocks_response = requests.get(blocks_url, headers=headers)
                    blocks_response.raise_for_status()
                    blocks_data = blocks_response.json()
                    
                    blocks = blocks_data.get('results', [])
                    
                    has_transcription = False
                    has_summary = False
                    
                    for block in blocks:
                        if block.get('type') == 'heading_2':
                            heading_text = block.get('heading_2', {}).get('rich_text', [])
                            if heading_text:
                                text_content = heading_text[0].get('text', {}).get('content', '')
                                if 'Транскрипция' in text_content:
                                    has_transcription = True
                                elif 'Саммари' in text_content:
                                    has_summary = True
                    
                    if has_transcription or has_summary:
                        events_with_notion_content += 1
                        if has_transcription:
                            events_with_transcription_content += 1
                        if has_summary:
                            events_with_summary_content += 1
                        
                        print(f"✅ {event_title}")
                        print(f"   📅 {start_time}")
                        print(f"   🆔 {event_id}")
                        print(f"   📝 Транскрипция: {'✅' if has_transcription else '❌'}")
                        print(f"   📊 Саммари: {'✅' if has_summary else '❌'}")
                        print()
                
                except Exception as e:
                    print(f"❌ {event_title} - Ошибка проверки: {e}")
            
            if events_with_notion_content == 0:
                print("❌ Событий с контентом в Notion не найдено")
            
            # Итоговая статистика
            print("📊 ИТОГОВАЯ СТАТИСТИКА:")
            print("=" * 50)
            print(f"📄 Всего событий: {total_events}")
            print(f"📄 Событий с Notion страницами: {events_with_notion}")
            print(f"📝 Событий с транскрипциями: {len(events_with_transcriptions)}")
            print(f"📊 Событий с саммари: {len(events_with_summaries)}")
            print(f"📄 Событий с контентом в Notion: {events_with_notion_content}")
            print(f"📝 Событий с транскрипциями в Notion: {events_with_transcription_content}")
            print(f"📊 Событий с саммари в Notion: {events_with_summary_content}")
            print()
            
            # Процент синхронизации
            if total_events > 0:
                print("📈 ПРОЦЕНТЫ СИНХРОНИЗАЦИИ:")
                print("-" * 30)
                notion_percent = (events_with_notion / total_events) * 100
                transcription_percent = (len(events_with_transcriptions) / total_events) * 100
                summary_percent = (len(events_with_summaries) / total_events) * 100
                notion_content_percent = (events_with_notion_content / total_events) * 100
                
                print(f"📄 Notion страницы: {notion_percent:.1f}%")
                print(f"📝 Транскрипции: {transcription_percent:.1f}%")
                print(f"📊 Саммари: {summary_percent:.1f}%")
                print(f"📄 Контент в Notion: {notion_content_percent:.1f}%")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка работы с базой данных: {e}")
        return False

if __name__ == "__main__":
    success = generate_sync_report()
    
    if success:
        print("✅ Отчет о синхронизации сгенерирован успешно!")
    else:
        print("❌ Ошибка генерации отчета!")
        sys.exit(1)
