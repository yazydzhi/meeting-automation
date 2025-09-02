#!/usr/bin/env python3
"""
Скрипт для связывания транскрипций с событиями.
"""

import os
import sys
import sqlite3
import re
from datetime import datetime

def link_transcriptions_to_events():
    """Связывает транскрипции с событиями на основе путей к файлам."""
    
    try:
        print("🔗 Связывание транскрипций с событиями...")
        print("=" * 50)
        
        # Подключаемся к SQLite базе данных
        db_path = "data/system_state.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем все транскрипции без event_id
        cursor.execute("""
            SELECT id, file_path, transcript_file, status
            FROM processed_transcriptions
            WHERE event_id IS NULL
            ORDER BY processed_at DESC
        """)
        
        transcriptions = cursor.fetchall()
        print(f"📊 Транскрипций без event_id: {len(transcriptions)}")
        
        if not transcriptions:
            print("✅ Все транскрипции уже связаны с событиями!")
            return True
        
        # Получаем все события
        cursor.execute("""
            SELECT event_id, event_title, event_start_time, account_type
            FROM processed_events
            ORDER BY event_start_time DESC
        """)
        
        events = cursor.fetchall()
        print(f"📊 Событий в базе: {len(events)}")
        
        # Создаем словарь событий для поиска
        events_dict = {}
        for event in events:
            event_id, event_title, event_start_time, account_type = event
            
            # Создаем ключи для поиска
            # 1. По названию события (очищенному)
            clean_title = re.sub(r'[^\w\s]', '', event_title.lower()).strip()
            events_dict[clean_title] = event_id
            
            # 2. По дате (если есть)
            if event_start_time:
                try:
                    date_str = event_start_time[:10]  # YYYY-MM-DD
                    events_dict[date_str] = event_id
                except:
                    pass
        
        # Связываем транскрипции с событиями
        linked_count = 0
        
        for transcription in transcriptions:
            transcription_id, file_path, transcript_file, status = transcription
            
            # Извлекаем информацию из пути к файлу
            # Пример пути: /Users/azg/Downloads/01 - yazydzhi@gmail.com/2025-08-21 16-00 Тестовая встреча/2025-08-21 18-00 Тестовая встреча_compressed.mp3
            
            # Ищем дату в пути
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_path)
            if date_match:
                date_str = date_match.group(1)
                
                # Ищем название события в пути
                # Извлекаем название из последней части пути
                path_parts = file_path.split('/')
                if len(path_parts) > 1:
                    folder_name = path_parts[-2]  # Папка с событием
                    
                    # Очищаем название от даты и времени
                    clean_folder_name = re.sub(r'\d{4}-\d{2}-\d{2}\s+\d{2}-\d{2}\s*', '', folder_name).strip()
                    clean_folder_name = re.sub(r'[^\w\s]', '', clean_folder_name.lower()).strip()
                    
                    # Ищем событие по дате и названию
                    found_event_id = None
                    
                    # Сначала по дате
                    if date_str in events_dict:
                        found_event_id = events_dict[date_str]
                    
                    # Затем по названию
                    if not found_event_id and clean_folder_name in events_dict:
                        found_event_id = events_dict[clean_folder_name]
                    
                    if found_event_id:
                        # Обновляем транскрипцию
                        cursor.execute('''
                            UPDATE processed_transcriptions 
                            SET event_id = ?
                            WHERE id = ?
                        ''', (found_event_id, transcription_id))
                        
                        linked_count += 1
                        print(f"  ✅ {file_path} -> {found_event_id}")
                    else:
                        print(f"  ❌ {file_path} -> событие не найдено")
                else:
                    print(f"  ⚠️ {file_path} -> неверный формат пути")
            else:
                print(f"  ⚠️ {file_path} -> дата не найдена в пути")
        
        conn.commit()
        
        print(f"\n📊 Результаты связывания:")
        print(f"  ✅ Связано транскрипций: {linked_count}")
        print(f"  ❌ Не связано: {len(transcriptions) - linked_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при связывании транскрипций: {e}")
        return False

if __name__ == "__main__":
    success = link_transcriptions_to_events()
    
    if success:
        print("\n✅ Связывание транскрипций завершено успешно!")
    else:
        print("\n❌ Связывание завершено с ошибками!")
        sys.exit(1)
