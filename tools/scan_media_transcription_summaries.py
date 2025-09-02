#!/usr/bin/env python3
"""
Скрипт для сканирования папок и поиска медиа файлов, транскрипций и саммари.
Обновляет базу данных с найденными файлами.
"""

import os
import sys
import sqlite3
from datetime import datetime
import json

# Добавляем корневую папку проекта в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config_manager import ConfigManager
from src.handlers.state_manager import StateManager

def scan_folder_for_files(folder_path, account_type):
    """
    Сканирует папку на наличие медиа файлов, транскрипций и саммари.
    
    Returns:
        dict: Словарь с найденными файлами
    """
    result = {
        'media_files': [],
        'transcription_files': [],
        'summary_files': [],
        'analysis_files': []
    }
    
    if not os.path.exists(folder_path):
        return result
    
    try:
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            
            if os.path.isfile(item_path):
                # Медиа файлы
                if item.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.m4a')):
                    result['media_files'].append(item_path)
                
                # Транскрипции
                elif item.endswith('__transcript.txt'):
                    result['transcription_files'].append(item_path)
                
                # Саммари
                elif item.endswith('_summary.txt'):
                    result['summary_files'].append(item_path)
                
                # Анализ
                elif item.endswith('_analysis.json'):
                    result['analysis_files'].append(item_path)
    
    except Exception as e:
        print(f"  ⚠️ Ошибка сканирования папки {folder_path}: {e}")
    
    return result

def scan_all_folders():
    """
    Сканирует все папки событий на наличие файлов.
    """
    print("🔍 Сканирование всех папок событий...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Получаем все события с папками
    cursor.execute('''
        SELECT pe.event_id, pe.event_title, pe.account_type, fcs.folder_path
        FROM processed_events pe
        INNER JOIN folder_creation_status fcs ON pe.event_id = fcs.event_id
        WHERE fcs.status = 'success'
        ORDER BY pe.processed_at DESC
    ''')
    
    events_with_folders = cursor.fetchall()
    conn.close()
    
    print(f"📊 Найдено {len(events_with_folders)} событий с папками")
    
    scan_results = []
    
    for event_id, event_title, account_type, folder_path in events_with_folders:
        print(f"\n📁 Сканирую: {event_title}")
        print(f"  📂 Папка: {folder_path}")
        
        files = scan_folder_for_files(folder_path, account_type)
        
        # Подсчитываем файлы
        media_count = len(files['media_files'])
        transcription_count = len(files['transcription_files'])
        summary_count = len(files['summary_files'])
        analysis_count = len(files['analysis_files'])
        
        print(f"  🎬 Медиа: {media_count}")
        print(f"  🎤 Транскрипции: {transcription_count}")
        print(f"  📋 Саммари: {summary_count}")
        print(f"  📊 Анализ: {analysis_count}")
        
        scan_results.append({
            'event_id': event_id,
            'event_title': event_title,
            'account_type': account_type,
            'folder_path': folder_path,
            'files': files,
            'counts': {
                'media': media_count,
                'transcription': transcription_count,
                'summary': summary_count,
                'analysis': analysis_count
            }
        })
    
    return scan_results

def update_database_with_scan_results(scan_results):
    """
    Обновляет базу данных с результатами сканирования.
    """
    print(f"\n🔧 Обновление базы данных с результатами сканирования...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    media_updated = 0
    transcription_updated = 0
    summary_updated = 0
    
    for result in scan_results:
        event_id = result['event_id']
        files = result['files']
        counts = result['counts']
        
        # Обновляем медиа файлы
        if counts['media'] > 0:
            for media_file in files['media_files']:
                # Проверяем, есть ли уже запись
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_media 
                    WHERE file_path = ? AND status = 'success'
                ''', (media_file,))
                
                if cursor.fetchone()[0] == 0:
                    try:
                        # Добавляем запись о медиа файле
                        cursor.execute('''
                            INSERT INTO processed_media 
                            (file_path, compressed_video, compressed_audio, status, processed_at)
                            VALUES (?, '', '', 'success', ?)
                        ''', (media_file, datetime.now().isoformat()))
                        media_updated += 1
                        print(f"  ✅ Добавлен медиа файл: {os.path.basename(media_file)}")
                    except sqlite3.IntegrityError:
                        print(f"  ⚠️ Медиа файл уже существует: {os.path.basename(media_file)}")
        
        # Обновляем транскрипции
        if counts['transcription'] > 0:
            for transcript_file in files['transcription_files']:
                # Проверяем, есть ли уже запись
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_transcriptions 
                    WHERE transcript_file = ? AND status = 'success'
                ''', (transcript_file,))
                
                if cursor.fetchone()[0] == 0:
                    # Находим соответствующий аудио файл
                    audio_file = transcript_file.replace('__transcript.txt', '_compressed.mp3')
                    if not os.path.exists(audio_file):
                        # Пробуем другие варианты
                        base_name = transcript_file.replace('__transcript.txt', '')
                        for ext in ['_compressed.mp3', '_compressed.wav', '.mp3', '.wav']:
                            test_file = base_name + ext
                            if os.path.exists(test_file):
                                audio_file = test_file
                                break
                    
                    try:
                        # Добавляем запись о транскрипции
                        cursor.execute('''
                            INSERT INTO processed_transcriptions 
                            (file_path, transcript_file, status, processed_at)
                            VALUES (?, ?, 'success', ?)
                        ''', (audio_file, transcript_file, datetime.now().isoformat()))
                        transcription_updated += 1
                        print(f"  ✅ Добавлена транскрипция: {os.path.basename(transcript_file)}")
                    except sqlite3.IntegrityError:
                        print(f"  ⚠️ Транскрипция уже существует: {os.path.basename(transcript_file)}")
        
        # Обновляем саммари
        if counts['summary'] > 0 or counts['analysis'] > 0:
            for summary_file in files['summary_files']:
                # Проверяем, есть ли уже запись
                cursor.execute('''
                    SELECT COUNT(*) FROM processed_summaries 
                    WHERE summary_file = ? AND status = 'success'
                ''', (summary_file,))
                
                if cursor.fetchone()[0] == 0:
                    # Находим соответствующий файл транскрипции
                    transcript_file = summary_file.replace('_summary.txt', '__transcript.txt')
                    if not os.path.exists(transcript_file):
                        transcript_file = ''
                    
                    # Находим соответствующий файл анализа
                    analysis_file = summary_file.replace('_summary.txt', '_analysis.json')
                    if not os.path.exists(analysis_file):
                        analysis_file = ''
                    
                    # Добавляем запись о саммари
                    cursor.execute('''
                        INSERT INTO processed_summaries 
                        (transcript_file, summary_file, analysis_file, status, created_at)
                        VALUES (?, ?, ?, 'success', ?)
                    ''', (transcript_file, summary_file, analysis_file, datetime.now().isoformat()))
                    summary_updated += 1
                    print(f"  ✅ Добавлено саммари: {os.path.basename(summary_file)}")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 Результаты обновления базы данных:")
    print(f"  🎬 Медиа файлов добавлено: {media_updated}")
    print(f"  🎤 Транскрипций добавлено: {transcription_updated}")
    print(f"  📋 Саммари добавлено: {summary_updated}")

def generate_scan_report(scan_results):
    """
    Генерирует отчет о сканировании.
    """
    print(f"\n📊 ОТЧЕТ О СКАНИРОВАНИИ ПАПОК")
    print("=" * 60)
    
    total_events = len(scan_results)
    events_with_media = sum(1 for r in scan_results if r['counts']['media'] > 0)
    events_with_transcription = sum(1 for r in scan_results if r['counts']['transcription'] > 0)
    events_with_summary = sum(1 for r in scan_results if r['counts']['summary'] > 0)
    
    total_media = sum(r['counts']['media'] for r in scan_results)
    total_transcription = sum(r['counts']['transcription'] for r in scan_results)
    total_summary = sum(r['counts']['summary'] for r in scan_results)
    
    print(f"📅 Всего событий с папками: {total_events}")
    print(f"🎬 Событий с медиа: {events_with_media} ({events_with_media/total_events*100:.1f}%)")
    print(f"🎤 Событий с транскрипциями: {events_with_transcription} ({events_with_transcription/total_events*100:.1f}%)")
    print(f"📋 Событий с саммари: {events_with_summary} ({events_with_summary/total_events*100:.1f}%)")
    print()
    print(f"📊 Общее количество файлов:")
    print(f"  🎬 Медиа файлов: {total_media}")
    print(f"  🎤 Транскрипций: {total_transcription}")
    print(f"  📋 Саммари: {total_summary}")
    
    # Детальный отчет по событиям с файлами
    print(f"\n📋 ДЕТАЛЬНЫЙ ОТЧЕТ:")
    print("-" * 60)
    
    for result in scan_results:
        if any(result['counts'].values()):
            print(f"\n📁 {result['event_title']}")
            print(f"  📂 {result['folder_path']}")
            if result['counts']['media'] > 0:
                print(f"  🎬 Медиа: {result['counts']['media']} файлов")
            if result['counts']['transcription'] > 0:
                print(f"  🎤 Транскрипции: {result['counts']['transcription']} файлов")
            if result['counts']['summary'] > 0:
                print(f"  📋 Саммари: {result['counts']['summary']} файлов")

def verify_database_state():
    """
    Проверяет состояние базы данных после обновления.
    """
    print(f"\n🔍 Проверка состояния базы данных...")
    
    conn = sqlite3.connect('data/system_state.db')
    cursor = conn.cursor()
    
    # Подсчитываем записи в каждой таблице
    cursor.execute('SELECT COUNT(*) FROM processed_media WHERE status = "success"')
    media_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM processed_transcriptions WHERE status = "success"')
    transcription_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM processed_summaries WHERE status = "success"')
    summary_count = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"📊 Состояние базы данных:")
    print(f"  🎬 Медиа файлов в БД: {media_count}")
    print(f"  🎤 Транскрипций в БД: {transcription_count}")
    print(f"  📋 Саммари в БД: {summary_count}")

if __name__ == "__main__":
    try:
        scan_results = scan_all_folders()
        update_database_with_scan_results(scan_results)
        generate_scan_report(scan_results)
        verify_database_state()
        print("\n✅ Сканирование и обновление базы данных завершено успешно!")
    except Exception as e:
        print(f"\n❌ Ошибка при сканировании: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
