#!/usr/bin/env python3
"""
Скрипт для связывания саммари с событиями.
"""

import os
import sys
import sqlite3
import re
from datetime import datetime

def link_summaries_to_events():
    """Связывает саммари с событиями на основе файлов транскрипций."""
    
    try:
        print("🔗 Связывание саммари с событиями...")
        print("=" * 50)
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все саммари без event_id
        cursor.execute("""
            SELECT id, transcript_file, summary_file, analysis_file, status
            FROM processed_summaries
            WHERE event_id IS NULL
            ORDER BY created_at DESC
        """)
        
        summaries = cursor.fetchall()
        print(f"📊 Саммари без event_id: {len(summaries)}")
        
        if not summaries:
            print("✅ Все саммари уже связаны с событиями!")
            return True
        
        # Получаем все транскрипции с event_id
        cursor.execute("""
            SELECT id, file_path, transcript_file, event_id
            FROM processed_transcriptions
            WHERE event_id IS NOT NULL
            ORDER BY processed_at DESC
        """)
        
        transcriptions = cursor.fetchall()
        print(f"📊 Транскрипций с event_id: {len(transcriptions)}")
        
        # Создаем словарь транскрипций для поиска
        transcriptions_dict = {}
        for transcription in transcriptions:
            transcription_id, file_path, transcript_file, event_id = transcription
            if transcript_file:
                transcriptions_dict[transcript_file] = event_id
        
        # Связываем саммари с событиями
        linked_count = 0
        
        for summary in summaries:
            summary_id, transcript_file, summary_file, analysis_file, status = summary
            
            # Ищем транскрипцию в словаре
            if transcript_file in transcriptions_dict:
                event_id = transcriptions_dict[transcript_file]
                
                # Обновляем саммари
                cursor.execute('''
                    UPDATE processed_summaries 
                    SET event_id = ?
                    WHERE id = ?
                ''', (event_id, summary_id))
                
                linked_count += 1
                print(f"  ✅ {transcript_file} -> {event_id}")
            else:
                print(f"  ❌ {transcript_file} -> транскрипция не найдена")
        
        conn.commit()
        
        print(f"\n📊 Результаты связывания:")
        print(f"  ✅ Связано саммари: {linked_count}")
        print(f"  ❌ Не связано: {len(summaries) - linked_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при связывании саммари: {e}")
        return False

if __name__ == "__main__":
    success = link_summaries_to_events()
    
    if success:
        print("\n✅ Связывание саммари завершено успешно!")
    else:
        print("\n❌ Связывание завершено с ошибками!")
        sys.exit(1)
