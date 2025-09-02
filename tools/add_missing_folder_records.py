#!/usr/bin/env python3
"""
Скрипт для добавления недостающих записей о папках в базу данных.
Находит события, для которых есть папки, но нет записей в folder_creation_status.
"""

import os
import sys
import sqlite3
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.state_manager import StateManager

def find_missing_folder_records():
    """
    Находит события, для которых есть папки, но нет записей в folder_creation_status.
    """
    print("🔍 Поиск событий с папками, но без записей в базе данных...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Получаем все события
    cursor.execute('SELECT event_id, event_title, account_type, event_start_time FROM processed_events')
    events = cursor.fetchall()
    
    missing_records = []
    
    for event_id, event_title, account_type, event_start_time in events:
        # Проверяем, есть ли запись в folder_creation_status
        cursor.execute('''
            SELECT COUNT(*) FROM folder_creation_status 
            WHERE event_id = ? AND account_type = ? AND status = 'success'
        ''', (event_id, account_type))
        
        if cursor.fetchone()[0] == 0:
            # Определяем путь к папке
            if account_type == 'personal':
                base_path = '/Users/azg/Downloads/01 - yazydzhi@gmail.com'
            else:
                base_path = '/Users/azg/Downloads/02 - v.yazydzhi@cian.ru'
            
            # Формируем имя папки на основе времени события
            if event_start_time:
                try:
                    # Парсим время события
                    event_time = datetime.fromisoformat(event_start_time.replace('Z', '+00:00'))
                    folder_name = event_time.strftime('%Y-%m-%d %H-%M') + ' ' + event_title
                    folder_path = os.path.join(base_path, folder_name)
                    
                    # Проверяем, существует ли папка
                    if os.path.exists(folder_path):
                        missing_records.append({
                            'event_id': event_id,
                            'event_title': event_title,
                            'account_type': account_type,
                            'folder_path': folder_path,
                            'event_start_time': event_start_time
                        })
                        print(f"  📁 Найдена папка: {folder_name}")
                    else:
                        # Попробуем найти папку с похожим именем
                        if os.path.exists(base_path):
                            for item in os.listdir(base_path):
                                item_path = os.path.join(base_path, item)
                                if os.path.isdir(item_path) and event_title in item:
                                    missing_records.append({
                                        'event_id': event_id,
                                        'event_title': event_title,
                                        'account_type': account_type,
                                        'folder_path': item_path,
                                        'event_start_time': event_start_time
                                    })
                                    print(f"  📁 Найдена похожая папка: {item}")
                                    break
                except Exception as e:
                    print(f"  ⚠️ Ошибка обработки времени для {event_title}: {e}")
    
    conn.close()
    
    print(f"\n📊 Найдено {len(missing_records)} событий с папками, но без записей в БД")
    return missing_records

def add_missing_records(missing_records):
    """
    Добавляет недостающие записи в folder_creation_status.
    """
    if not missing_records:
        print("✅ Нет недостающих записей для добавления")
        return
    
    print(f"\n🔧 Добавление {len(missing_records)} записей в folder_creation_status...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    added_count = 0
    
    for record in missing_records:
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
            print(f"  ✅ Добавлено: {record['event_title']}")
            
        except sqlite3.IntegrityError:
            print(f"  ⚠️ Запись уже существует: {record['event_title']}")
        except Exception as e:
            print(f"  ❌ Ошибка добавления {record['event_title']}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Добавлено записей: {added_count}")

def verify_result():
    """
    Проверяет результат добавления записей.
    """
    print("\n🔍 Проверка результата...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Проверяем, сколько событий имеют папки
    cursor.execute('''
        SELECT COUNT(DISTINCT pe.event_id) 
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id 
        WHERE fcs.status = 'success'
    ''')
    
    events_with_folders = cursor.fetchone()[0]
    
    # Общее количество событий
    cursor.execute('SELECT COUNT(*) FROM processed_events')
    total_events = cursor.fetchone()[0]
    
    # Количество записей в folder_creation_status
    cursor.execute('SELECT COUNT(*) FROM folder_creation_status')
    total_folders = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Статистика после добавления:")
    print(f"  📅 Всего событий: {total_events}")
    print(f"  📁 Всего записей о папках: {total_folders}")
    print(f"  ✅ Событий с папками: {events_with_folders}")
    print(f"  📈 Процент покрытия: {(events_with_folders/total_events*100):.1f}%")

if __name__ == "__main__":
    try:
        missing_records = find_missing_folder_records()
        add_missing_records(missing_records)
        verify_result()
        print("\n✅ Добавление недостающих записей завершено успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка при добавлении записей: {e}")
        sys.exit(1)
