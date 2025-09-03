#!/usr/bin/env python3
"""
Скрипт для синхронизации уже существующего контента в Notion страницы
"""

import sqlite3
import requests
import os
import json
from dotenv import load_dotenv

def load_config():
    """Загружает конфигурацию из .env"""
    load_dotenv()
    return {
        'notion_token': os.getenv('NOTION_TOKEN'),
        'db_path': 'data/system_state.db'
    }

def get_notion_headers(notion_token):
    """Возвращает заголовки для Notion API"""
    return {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }

def create_transcript_blocks(transcript_file_path):
    """Создает блоки для транскрипции."""
    try:
        blocks = []
        
        # Заголовок транскрипции
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📝 Транскрипция встречи"}}]
            }
        })
        
        # Читаем файл транскрипции
        if os.path.exists(transcript_file_path):
            with open(transcript_file_path, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            
            # Разбиваем на части (лимит Notion - 2000 символов на блок)
            chunk_size = 1800
            transcript_chunks = [transcript_content[i:i+chunk_size] for i in range(0, len(transcript_content), chunk_size)]
            
            for chunk in transcript_chunks:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
        
        return blocks
        
    except Exception as e:
        print(f"❌ Ошибка создания блоков транскрипции: {e}")
        return []

def create_summary_blocks(summary_file_path):
    """Создает блоки для саммари."""
    try:
        blocks = []
        
        # Заголовок саммари
        blocks.append({
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📊 Саммари встречи"}}]
            }
        })
        
        # Читаем файл саммари
        if os.path.exists(summary_file_path):
            with open(summary_file_path, 'r', encoding='utf-8') as f:
                summary_content = f.read()
            
            # Разбиваем на части
            chunk_size = 1800
            summary_chunks = [summary_content[i:i+chunk_size] for i in range(0, len(summary_content), chunk_size)]
            
            for chunk in summary_chunks:
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": chunk}}]
                    }
                })
        
        return blocks
        
    except Exception as e:
        print(f"❌ Ошибка создания блоков саммари: {e}")
        return []

def add_blocks_to_page(page_id, blocks, notion_token):
    """Добавляет блоки на страницу Notion."""
    try:
        headers = {
            'Authorization': f'Bearer {notion_token}',
            'Notion-Version': '2022-06-28',
            'Content-Type': 'application/json'
        }
        
        # Добавляем блоки по частям (лимит API)
        chunk_size = 50
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i:i+chunk_size]
            
            url = f'https://api.notion.com/v1/blocks/{page_id}/children'
            payload = {'children': chunk}
            
            response = requests.patch(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                print(f"❌ Ошибка добавления блоков: {response.status_code} - {response.text}")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка добавления блоков на страницу: {e}")
        return False

def sync_event_content(event_id, page_id, config):
    """Синхронизирует контент для конкретного события."""
    print(f"🔄 Синхронизация контента для события: {event_id}")
    
    # Подключаемся к БД
    conn = sqlite3.connect(config['db_path'])
    cursor = conn.cursor()
    
    # Получаем данные транскрипции
    cursor.execute('''
        SELECT transcript_file FROM processed_transcriptions
        WHERE event_id = ? AND status = 'success'
    ''', (event_id,))
    
    transcript_result = cursor.fetchone()
    transcript_file = transcript_result[0] if transcript_result else None
    
    # Получаем данные саммари
    cursor.execute('''
        SELECT summary_file FROM processed_summaries
        WHERE event_id = ? AND status = 'success'
    ''', (event_id,))
    
    summary_result = cursor.fetchone()
    summary_file = summary_result[0] if summary_result else None
    
    conn.close()
    
    if not transcript_file and not summary_file:
        print(f"   ℹ️ Нет контента для синхронизации")
        return True
    
    # Подготавливаем блоки для добавления
    blocks_to_add = []
    
    # Добавляем транскрипцию если есть
    if transcript_file and os.path.exists(transcript_file):
        transcript_blocks = create_transcript_blocks(transcript_file)
        blocks_to_add.extend(transcript_blocks)
        print(f"   📝 Добавлена транскрипция: {len(transcript_blocks)} блоков")
    
    # Добавляем саммари если есть
    if summary_file and os.path.exists(summary_file):
        summary_blocks = create_summary_blocks(summary_file)
        blocks_to_add.extend(summary_blocks)
        print(f"   📊 Добавлено саммари: {len(summary_blocks)} блоков")
    
    # Добавляем блоки на страницу
    if blocks_to_add:
        success = add_blocks_to_page(page_id, blocks_to_add, config['notion_token'])
        if success:
            print(f"   ✅ Контент успешно добавлен на страницу")
            
            # Записываем статус синхронизации в БД
            record_sync_status(event_id, transcript_file, summary_file, config)
            return True
        else:
            print(f"   ❌ Ошибка добавления контента на страницу")
            return False
    else:
        print(f"   ⚠️ Нет блоков для добавления")
        return True

def record_sync_status(event_id, transcript_file, summary_file, config):
    """Записывает статус синхронизации в БД."""
    try:
        conn = sqlite3.connect(config['db_path'])
        cursor = conn.cursor()
        
        # Записываем статус для транскрипции
        if transcript_file:
            cursor.execute('''
                INSERT OR REPLACE INTO notion_content_sync 
                (event_id, content_type, sync_status, synced_at, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (event_id, 'transcription', 'success', '2025-09-03T13:30:00', None))
        
        # Записываем статус для саммари
        if summary_file:
            cursor.execute('''
                INSERT OR REPLACE INTO notion_content_sync 
                (event_id, content_type, sync_status, synced_at, error_message, created_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (event_id, 'summary', 'success', '2025-09-03T13:30:00', None))
        
        conn.commit()
        conn.close()
        
        print(f"   📝 Статус синхронизации записан в БД")
        
    except Exception as e:
        print(f"   ❌ Ошибка записи статуса: {e}")

def main():
    """Основная функция"""
    config = load_config()
    
    if not config['notion_token']:
        print("❌ NOTION_TOKEN не найден в переменных окружения")
        return
    
    # Подключаемся к БД
    conn = sqlite3.connect(config['db_path'])
    cursor = conn.cursor()
    
    # Получаем события с контентом и Notion страницами
    cursor.execute('''
        SELECT DISTINCT 
            pe.event_id, 
            pe.event_title,
            nss.page_id
        FROM processed_events pe
        JOIN notion_sync_status nss ON pe.event_id = nss.event_id
        WHERE nss.sync_status = 'success'
        AND (
            EXISTS (SELECT 1 FROM processed_transcriptions pt WHERE pt.event_id = pe.event_id AND pt.status = 'success')
            OR EXISTS (SELECT 1 FROM processed_summaries ps WHERE ps.event_id = pe.event_id AND ps.status = 'success')
        )
        ORDER BY pe.event_start_time DESC
    ''')
    
    events = cursor.fetchall()
    conn.close()
    
    print(f"🎯 Синхронизация контента для {len(events)} событий")
    print("=" * 60)
    
    success_count = 0
    error_count = 0
    
    for event_id, event_title, page_id in events:
        try:
            title_short = event_title[:50] + '...' if len(event_title) > 50 else event_title
            print(f"\n📋 {title_short}")
            
            success = sync_event_content(event_id, page_id, config)
            if success:
                success_count += 1
            else:
                error_count += 1
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            error_count += 1
    
    print("\n" + "=" * 60)
    print(f"🎉 СИНХРОНИЗАЦИЯ ЗАВЕРШЕНА!")
    print(f"   ✅ Успешно: {success_count}")
    print(f"   ❌ Ошибок: {error_count}")
    print(f"   📊 Всего: {len(events)}")

if __name__ == "__main__":
    main()
