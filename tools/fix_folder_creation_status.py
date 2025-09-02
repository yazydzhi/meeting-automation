#!/usr/bin/env python3
"""
Скрипт для исправления несоответствия event_id в таблице folder_creation_status.
Обновляет старые хеш-based ID на новые ical-based ID.
"""

import os
import sys
import sqlite3
import hashlib
from datetime import datetime

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.state_manager import StateManager

def extract_ical_id_from_hash(hash_id: str) -> str:
    """
    Извлекает ical ID из хеша, если это возможно.
    """
    # Попробуем найти соответствующий ical ID в processed_events
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Ищем по части хеша
    hash_prefix = hash_id[:8]  # Берем первые 8 символов
    cursor.execute('''
        SELECT event_id FROM processed_events 
        WHERE event_id LIKE ? 
        LIMIT 1
    ''', (f'%{hash_prefix}%',))
    
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None

def fix_folder_creation_status():
    """
    Исправляет несоответствие event_id в таблице folder_creation_status.
    """
    print("🔧 Исправление несоответствия event_id в folder_creation_status...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Получаем все записи из folder_creation_status
    cursor.execute('SELECT event_id, folder_path, account_type, status, created_at FROM folder_creation_status')
    folder_records = cursor.fetchall()
    
    print(f"📊 Найдено {len(folder_records)} записей в folder_creation_status")
    
    updated_count = 0
    deleted_count = 0
    
    for record in folder_records:
        old_event_id, folder_path, account_type, status, created_at = record
        
        # Проверяем, является ли это старым хеш-based ID
        if not old_event_id.startswith('ical_'):
            print(f"🔄 Обрабатываю старый ID: {old_event_id}")
            
            # Ищем соответствующий ical ID
            new_event_id = extract_ical_id_from_hash(old_event_id)
            
            if new_event_id:
                print(f"  ✅ Найден новый ID: {new_event_id}")
                
                # Проверяем, есть ли уже запись с новым ID
                cursor.execute('''
                    SELECT COUNT(*) FROM folder_creation_status 
                    WHERE event_id = ? AND account_type = ?
                ''', (new_event_id, account_type))
                
                if cursor.fetchone()[0] == 0:
                    # Обновляем запись
                    cursor.execute('''
                        UPDATE folder_creation_status 
                        SET event_id = ? 
                        WHERE event_id = ? AND account_type = ?
                    ''', (new_event_id, old_event_id, account_type))
                    
                    updated_count += 1
                    print(f"  ✅ Обновлено: {old_event_id} -> {new_event_id}")
                else:
                    # Удаляем дубликат
                    cursor.execute('''
                        DELETE FROM folder_creation_status 
                        WHERE event_id = ? AND account_type = ?
                    ''', (old_event_id, account_type))
                    
                    deleted_count += 1
                    print(f"  🗑️ Удален дубликат: {old_event_id}")
            else:
                print(f"  ❌ Не найден соответствующий ical ID для: {old_event_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Результат исправления:")
    print(f"  ✅ Обновлено записей: {updated_count}")
    print(f"  🗑️ Удалено дубликатов: {deleted_count}")
    print(f"  📁 Всего записей в folder_creation_status: {len(folder_records)}")

def verify_fix():
    """
    Проверяет результат исправления.
    """
    print("\n🔍 Проверка результата исправления...")
    
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
    
    print(f"📊 Статистика после исправления:")
    print(f"  📅 Всего событий: {total_events}")
    print(f"  📁 Всего записей о папках: {total_folders}")
    print(f"  ✅ Событий с папками: {events_with_folders}")
    print(f"  📈 Процент покрытия: {(events_with_folders/total_events*100):.1f}%")

if __name__ == "__main__":
    try:
        fix_folder_creation_status()
        verify_fix()
        print("\n✅ Исправление завершено успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка при исправлении: {e}")
        sys.exit(1)
