#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для заполнения БД данными о уже созданных папках и страницах Notion.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from config_manager import ConfigManager
from handlers.state_manager import StateManager


def populate_existing_folders():
    """Заполняет БД данными о существующих папках."""
    print("📁 Заполнение данных о существующих папках...")
    
    try:
        config_manager = ConfigManager()
        state_manager = StateManager()
        
        # Получаем конфигурации аккаунтов
        personal_config = config_manager.get_personal_config()
        work_config = config_manager.get_work_config()
        
        folders_added = 0
        
        # Обрабатываем личный аккаунт
        if personal_config and personal_config.get('local_drive_root'):
            personal_folder = personal_config['local_drive_root']
            if os.path.exists(personal_folder):
                print(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                folders_added += process_folder_directory(personal_folder, "personal", state_manager)
        
        # Обрабатываем рабочий аккаунт
        if work_config and work_config.get('local_drive_root'):
            work_folder = work_config['local_drive_root']
            if os.path.exists(work_folder):
                print(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                folders_added += process_folder_directory(work_folder, "work", state_manager)
        
        print(f"✅ Добавлено {folders_added} папок в БД")
        
    except Exception as e:
        print(f"❌ Ошибка заполнения данных о папках: {e}")


def process_folder_directory(base_path: str, account_type: str, state_manager: StateManager) -> int:
    """Обрабатывает директорию с папками встреч."""
    folders_added = 0
    
    try:
        for item in os.listdir(base_path):
            item_path = os.path.join(base_path, item)
            
            # Проверяем, что это папка и она соответствует формату даты
            if os.path.isdir(item_path) and item.startswith('2025-'):
                # Извлекаем информацию о событии из имени папки
                event_id = generate_event_id_from_folder_name(item)
                
                # Проверяем, есть ли уже запись в БД
                if not state_manager.is_folder_created(event_id, account_type):
                    # Добавляем в БД
                    state_manager.mark_folder_created(event_id, item_path, account_type, "success")
                    folders_added += 1
                    print(f"  📁 Добавлена папка: {item}")
                else:
                    print(f"  ⏭️ Папка уже в БД: {item}")
    
    except Exception as e:
        print(f"❌ Ошибка обработки директории {base_path}: {e}")
    
    return folders_added


def generate_event_id_from_folder_name(folder_name: str) -> str:
    """Генерирует event_id из имени папки."""
    # Убираем дату и время из начала имени папки
    # Формат: "2025-08-21 18-00 Название встречи"
    parts = folder_name.split(' ', 2)
    if len(parts) >= 3:
        # Используем название встречи для генерации ID
        meeting_name = parts[2]
        import hashlib
        return hashlib.md5(meeting_name.encode('utf-8')).hexdigest()[:12]
    else:
        # Fallback: используем полное имя папки
        import hashlib
        return hashlib.md5(folder_name.encode('utf-8')).hexdigest()[:12]


def populate_existing_summaries():
    """Заполняет БД данными о существующих саммари."""
    print("📋 Заполнение данных о существующих саммари...")
    
    try:
        config_manager = ConfigManager()
        state_manager = StateManager()
        
        # Получаем конфигурации аккаунтов
        personal_config = config_manager.get_personal_config()
        work_config = config_manager.get_work_config()
        
        summaries_added = 0
        
        # Обрабатываем личный аккаунт
        if personal_config and personal_config.get('local_drive_root'):
            personal_folder = personal_config['local_drive_root']
            if os.path.exists(personal_folder):
                print(f"👤 Обрабатываю саммари личного аккаунта: {personal_folder}")
                summaries_added += process_summaries_directory(personal_folder, state_manager)
        
        # Обрабатываем рабочий аккаунт
        if work_config and work_config.get('local_drive_root'):
            work_folder = work_config['local_drive_root']
            if os.path.exists(work_folder):
                print(f"🏢 Обрабатываю саммари рабочего аккаунта: {work_folder}")
                summaries_added += process_summaries_directory(work_folder, state_manager)
        
        print(f"✅ Добавлено {summaries_added} саммари в БД")
        
    except Exception as e:
        print(f"❌ Ошибка заполнения данных о саммари: {e}")


def process_summaries_directory(base_path: str, state_manager: StateManager) -> int:
    """Обрабатывает директорию с саммари."""
    summaries_added = 0
    
    try:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith('_transcript.txt'):
                    transcript_file = os.path.join(root, file)
                    
                    # Проверяем, есть ли уже запись в БД
                    if not state_manager.is_summary_processed(transcript_file):
                        # Генерируем пути к файлам саммари
                        base_name = os.path.splitext(transcript_file)[0]
                        summary_file = base_name + '_summary.txt'
                        analysis_file = base_name + '_analysis.json'
                        
                        # Проверяем существование файлов саммари
                        if os.path.exists(summary_file) and os.path.exists(analysis_file):
                            # Добавляем в БД
                            state_manager.mark_summary_processed(
                                transcript_file, 
                                summary_file, 
                                analysis_file, 
                                "success"
                            )
                            summaries_added += 1
                            print(f"  📋 Добавлено саммари: {os.path.basename(transcript_file)}")
                        else:
                            print(f"  ⏭️ Саммари не найдено: {os.path.basename(transcript_file)}")
                    else:
                        print(f"  ⏭️ Саммари уже в БД: {os.path.basename(transcript_file)}")
    
    except Exception as e:
        print(f"❌ Ошибка обработки саммари в {base_path}: {e}")
    
    return summaries_added


def populate_existing_media():
    """Заполняет БД данными о существующих медиа файлах."""
    print("🎥 Заполнение данных о существующих медиа файлах...")
    
    try:
        config_manager = ConfigManager()
        state_manager = StateManager()
        
        # Получаем конфигурации аккаунтов
        personal_config = config_manager.get_personal_config()
        work_config = config_manager.get_work_config()
        
        media_added = 0
        
        # Обрабатываем личный аккаунт
        if personal_config and personal_config.get('local_drive_root'):
            personal_folder = personal_config['local_drive_root']
            if os.path.exists(personal_folder):
                print(f"👤 Обрабатываю медиа личного аккаунта: {personal_folder}")
                media_added += process_media_directory(personal_folder, state_manager)
        
        # Обрабатываем рабочий аккаунт
        if work_config and work_config.get('local_drive_root'):
            work_folder = work_config['local_drive_root']
            if os.path.exists(work_folder):
                print(f"🏢 Обрабатываю медиа рабочего аккаунта: {work_folder}")
                media_added += process_media_directory(work_folder, state_manager)
        
        print(f"✅ Добавлено {media_added} медиа файлов в БД")
        
    except Exception as e:
        print(f"❌ Ошибка заполнения данных о медиа: {e}")


def process_media_directory(base_path: str, state_manager: StateManager) -> int:
    """Обрабатывает директорию с медиа файлами."""
    media_added = 0
    
    try:
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                    media_file = os.path.join(root, file)
                    
                    # Проверяем, есть ли уже запись в БД
                    if not state_manager.is_media_processed(media_file):
                        # Ищем сжатые файлы
                        base_name = os.path.splitext(media_file)[0]
                        compressed_video = base_name + '_compressed.mp4'
                        compressed_audio = base_name + '_compressed.mp3'
                        
                        # Проверяем существование сжатых файлов
                        if os.path.exists(compressed_video) and os.path.exists(compressed_audio):
                            # Добавляем в БД
                            state_manager.mark_media_processed(
                                media_file, 
                                compressed_video, 
                                compressed_audio, 
                                "success"
                            )
                            media_added += 1
                            print(f"  🎥 Добавлен медиа файл: {os.path.basename(media_file)}")
                        else:
                            print(f"  ⏭️ Сжатые файлы не найдены: {os.path.basename(media_file)}")
                    else:
                        print(f"  ⏭️ Медиа файл уже в БД: {os.path.basename(media_file)}")
    
    except Exception as e:
        print(f"❌ Ошибка обработки медиа в {base_path}: {e}")
    
    return media_added


def main():
    """Основная функция."""
    print("🚀 Запуск заполнения БД существующими данными...")
    print("=" * 60)
    
    # Заполняем данные о папках
    populate_existing_folders()
    print()
    
    # Заполняем данные о саммари
    populate_existing_summaries()
    print()
    
    # Заполняем данные о медиа
    populate_existing_media()
    print()
    
    print("=" * 60)
    print("✅ Заполнение БД завершено!")


if __name__ == "__main__":
    main()
