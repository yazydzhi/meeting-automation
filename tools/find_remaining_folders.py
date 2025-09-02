#!/usr/bin/env python3
"""
Скрипт для поиска оставшихся папок, которые не были найдены предыдущим скриптом.
"""

import os
import sys
import sqlite3
from datetime import datetime

def find_remaining_folders():
    """
    Находит оставшиеся папки для событий без записей в folder_creation_status.
    """
    print("🔍 Поиск оставшихся папок...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Получаем события без папок
    cursor.execute('''
        SELECT event_id, event_title, account_type, event_start_time 
        FROM processed_events 
        WHERE event_id NOT IN (
            SELECT event_id FROM folder_creation_status WHERE status = 'success'
        )
        ORDER BY processed_at DESC
    ''')
    
    events_without_folders = cursor.fetchall()
    
    print(f"📊 Найдено {len(events_without_folders)} событий без папок в БД")
    
    found_folders = []
    
    for event_id, event_title, account_type, event_start_time in events_without_folders:
        print(f"\n🔍 Ищем папку для: {event_title}")
        
        # Определяем базовый путь
        if account_type == 'personal':
            base_path = '/Users/azg/Downloads/01 - yazydzhi@gmail.com'
        else:
            base_path = '/Users/azg/Downloads/02 - v.yazydzhi@cian.ru'
        
        if not os.path.exists(base_path):
            print(f"  ❌ Базовый путь не существует: {base_path}")
            continue
        
        # Ищем папки, содержащие ключевые слова из названия события
        found = False
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            if os.path.isdir(item_path):
                # Проверяем различные варианты совпадения
                if (event_title in item or 
                    any(word in item for word in event_title.split() if len(word) > 3) or
                    item.replace('_', ' ').replace('-', ' ') in event_title.replace('_', ' ').replace('-', ' ')):
                    
                    found_folders.append({
                        'event_id': event_id,
                        'event_title': event_title,
                        'account_type': account_type,
                        'folder_path': item_path,
                        'folder_name': item
                    })
                    print(f"  ✅ Найдена папка: {item}")
                    found = True
                    break
        
        if not found:
            print(f"  ❌ Папка не найдена")
    
    conn.close()
    
    print(f"\n📊 Найдено {len(found_folders)} папок для добавления в БД")
    return found_folders

def add_found_folders(found_folders):
    """
    Добавляет найденные папки в folder_creation_status.
    """
    if not found_folders:
        print("✅ Нет папок для добавления")
        return
    
    print(f"\n🔧 Добавление {len(found_folders)} записей в folder_creation_status...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    added_count = 0
    
    for record in found_folders:
        try:
            cursor.execute('''
                INSERT INTO folder_creation_status 
                (event_id, folder_path, account_type, status, created_at)
                VALUES (?, ?, ?, 'success', ?)
            ''', (
                record['event_id'],
                record['folder_path'],
                record['account_type'],
                datetime.now().isoformat()
            ))
            
            added_count += 1
            print(f"  ✅ Добавлено: {record['event_title']} -> {record['folder_name']}")
            
        except sqlite3.IntegrityError:
            print(f"  ⚠️ Запись уже существует: {record['event_title']}")
        except Exception as e:
            print(f"  ❌ Ошибка добавления {record['event_title']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Добавлено записей: {added_count}")

def verify_final_result():
    """
    Проверяет финальный результат.
    """
    print("\n🔍 Финальная проверка...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Общее количество событий
    cursor.execute('SELECT COUNT(*) FROM processed_events')
    total_events = cursor.fetchone()[0]
    
    # События с папками
    cursor.execute('''
        SELECT COUNT(DISTINCT pe.event_id) 
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id 
        WHERE fcs.status = 'success'
    ''')
    events_with_folders = cursor.fetchone()[0]
    
    # События без папок
    cursor.execute('''
        SELECT COUNT(*) FROM processed_events 
        WHERE event_id NOT IN (
            SELECT event_id FROM folder_creation_status WHERE status = 'success'
        )
    ''')
    events_without_folders = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Финальная статистика:")
    print(f"  📅 Всего событий: {total_events}")
    print(f"  ✅ Событий с папками: {events_with_folders}")
    print(f"  ❌ Событий без папок: {events_without_folders}")
    print(f"  📈 Процент покрытия: {(events_with_folders/total_events*100):.1f}%")
    
    if events_without_folders > 0:
        print(f"\n📋 События без папок:")
        conn = sqlite3.connect('data/system_state.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT event_title, account_type FROM processed_events 
            WHERE event_id NOT IN (
                SELECT event_id FROM folder_creation_status WHERE status = 'success'
            )
            ORDER BY processed_at DESC
        ''')
        for title, account in cursor.fetchall():
            print(f"  - {title} ({account})")
        conn.close()

if __name__ == "__main__":
    try:
        found_folders = find_remaining_folders()
        add_found_folders(found_folders)
        verify_final_result()
        print("\n✅ Поиск и добавление оставшихся папок завершено!")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)
