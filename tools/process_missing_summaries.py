#!/usr/bin/env python3
"""
Скрипт для обработки саммари для событий с транскрипциями, но без саммари.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.state_manager import StateManager
from src.handlers.summary_handler import SummaryHandler

def find_events_with_transcriptions_but_no_summaries():
    """
    Находит события с транскрипциями, но без саммари.
    """
    print("🔍 Поиск событий с транскрипциями, но без саммари...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Находим события с папками
    cursor.execute('''
        SELECT pe.event_id, pe.event_title, pe.account_type, fcs.folder_path
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id
        WHERE fcs.status = 'success'
        ORDER BY pe.processed_at DESC
    ''')
    
    events_with_folders = cursor.fetchall()
    conn.close()
    
    events_needing_summaries = []
    
    for event_id, event_title, account_type, folder_path in events_with_folders:
        # Проверяем, есть ли транскрипции в папке
        transcript_files = []
        if os.path.exists(folder_path):
            for item in os.listdir(folder_path):
                if item.endswith('__transcript.txt'):
                    transcript_files.append(os.path.join(folder_path, item))
        
        if transcript_files:
            # Проверяем, есть ли саммари для этих транскрипций
            has_summaries = False
            for transcript_file in transcript_files:
                summary_file = transcript_file.replace('__transcript.txt', '_summary.txt')
                if os.path.exists(summary_file):
                    has_summaries = True
                    break
            
            if not has_summaries:
                events_needing_summaries.append({
                    'event_id': event_id,
                    'event_title': event_title,
                    'account_type': account_type,
                    'folder_path': folder_path,
                    'transcript_files': transcript_files
                })
                print(f"  📋 {event_title}: {len(transcript_files)} транскрипций без саммари")
    
    print(f"\n📊 Найдено {len(events_needing_summaries)} событий, нуждающихся в саммари")
    return events_needing_summaries

def process_summaries_for_events(events):
    """
    Обрабатывает саммари для списка событий.
    """
    if not events:
        print("✅ Все события уже имеют саммари")
        return
    
    print(f"\n🔧 Обработка саммари для {len(events)} событий...")
    
    try:
        # Инициализируем компоненты
        config_manager = ConfigManager()
        state_manager = StateManager()
        summary_handler = SummaryHandler(config_manager)
        
        success_count = 0
        error_count = 0
        
        for event in events:
            event_title = event['event_title']
            account_type = event['account_type']
            folder_path = event['folder_path']
            transcript_files = event['transcript_files']
            
            print(f"\n📋 Обработка саммари для: {event_title}")
            print(f"  📂 Папка: {folder_path}")
            print(f"  🎤 Транскрипций: {len(transcript_files)}")
            
            try:
                # Обрабатываем саммари для папки
                result = summary_handler._process_folder_summaries(folder_path, account_type)
                
                if result and result.get('processed', 0) > 0:
                    print(f"  ✅ Саммари создано: {result['processed']} файлов")
                    success_count += 1
                else:
                    print(f"  ❌ Ошибка создания саммари: {result}")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ❌ Ошибка обработки: {e}")
                error_count += 1
        
        print(f"\n📊 Результат обработки саммари:")
        print(f"  ✅ Успешно обработано: {success_count}")
        print(f"  ❌ Ошибок: {error_count}")
        print(f"  📈 Процент успеха: {(success_count/(success_count+error_count)*100):.1f}%")
        
    except Exception as e:
        print(f"❌ Критическая ошибка при обработке саммари: {e}")
        import traceback
        traceback.print_exc()

def verify_summary_results():
    """
    Проверяет результаты обработки саммари.
    """
    print(f"\n🔍 Проверка результатов обработки саммари...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Подсчитываем саммари в базе данных
    cursor.execute('SELECT COUNT(*) FROM processed_summaries WHERE status = "success"')
    total_summaries = cursor.fetchone()[0]
    
    # Подсчитываем транскрипции
    cursor.execute('SELECT COUNT(*) FROM processed_transcriptions WHERE status = "success"')
    total_transcriptions = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Статистика саммари:")
    print(f"  🎤 Транскрипций в БД: {total_transcriptions}")
    print(f"  📋 Саммари в БД: {total_summaries}")
    
    if total_transcriptions > 0:
        coverage = (total_summaries / total_transcriptions) * 100
        print(f"  📈 Покрытие саммари: {coverage:.1f}%")

if __name__ == "__main__":
    try:
        events = find_events_with_transcriptions_but_no_summaries()
        process_summaries_for_events(events)
        verify_summary_results()
        print(f"\n✅ Обработка саммари завершена!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
