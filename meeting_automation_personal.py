#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматизации встреч для ЛИЧНОГО аккаунта
Использует стандартные Google API провайдеры
"""

import os
import sys
import argparse
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List

# Добавляем src в путь
sys.path.insert(0, 'src')

try:
    from calendar_alternatives import get_calendar_provider, CalendarEvent
    from drive_alternatives import get_drive_provider, DriveFile
    from config_manager import ConfigManager
    from notion_templates import create_page_with_template
    from media_processor import get_media_processor
    from drive_sync import get_drive_sync
    from audio_processor import AudioProcessor
    from processing_status import ProcessingStatus
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/personal_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_personal_exclusions() -> List[str]:
    """Загрузить список личных ключевых слов для исключения из файла."""
    exclusions_file = Path("config/personal_exclusions.txt")
    exclusions = []
    
    if not exclusions_file.exists():
        logger.warning(f"⚠️ Файл исключений не найден: {exclusions_file}")
        # Возвращаем базовый список по умолчанию
        return ['День рождения', 'Дела', 'Личное', 'Personal', 'Отпуск']
    
    try:
        with open(exclusions_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Игнорируем пустые строки и комментарии
                if line and not line.startswith('#'):
                    exclusions.append(line)
        
        logger.info(f"📋 Загружено {len(exclusions)} исключений из {exclusions_file}")
        return exclusions
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки исключений: {e}")
        # Возвращаем базовый список по умолчанию
        return ['День рождения', 'Дела', 'Личное', 'Personal', 'Отпуск']

def load_personal_environment():
    """Загрузить переменные окружения для личного аккаунта."""
    try:
        # Пытаемся загрузить конфигурацию личного аккаунта
        if os.path.exists('env.personal'):
            from dotenv import load_dotenv
            load_dotenv('env.personal')
            logger.info("✅ Загружена конфигурация личного аккаунта")
        else:
            logger.warning("⚠️ Файл env.personal не найден, используем .env")
            from dotenv import load_dotenv
            load_dotenv()
        
        # Проверяем обязательные переменные для API
        required_vars = [
            'GOOGLE_CREDENTIALS',
            'PERSONAL_CALENDAR_ID',
            'PERSONAL_DRIVE_PARENT_ID',
            'NOTION_TOKEN',
            'NOTION_DATABASE_ID',
            'TELEGRAM_BOT_TOKEN',
            'TELEGRAM_CHAT_ID'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
            return False
        
        logger.info("✅ Переменные окружения загружены")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки переменных окружения: {e}")
        return False

def get_personal_calendar_provider():
    """Получить провайдер календаря для личного аккаунта (Google API)."""
    try:
        config = ConfigManager('env.personal' if os.path.exists('env.personal') else '.env')
        calendar_type = config.get_calendar_provider_type()
        calendar_config = config.get_calendar_provider_config()
        
        logger.info(f"📅 Используем провайдер календаря: {calendar_type}")
        
        # Для личного аккаунта используем Google API
        if calendar_type != 'google_api':
            logger.warning(f"⚠️ Для личного аккаунта рекомендуется google_api, текущий: {calendar_type}")
        
        return get_calendar_provider(calendar_type, **calendar_config)
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдера календаря: {e}")
        return None

def get_personal_drive_provider():
    """Получить провайдер Google Drive для личного аккаунта (Google API)."""
    try:
        config = ConfigManager('env.personal' if os.path.exists('env.personal') else '.env')
        drive_type = config.get_drive_provider_type()
        drive_config = config.get_drive_provider_config()
        
        logger.info(f"💾 Используем провайдер Google Drive: {drive_type}")
        
        # Для личного аккаунта используем Google API
        if drive_type != 'google_api':
            logger.warning(f"⚠️ Для личного аккаунта рекомендуется google_api, текущий: {drive_type}")
        
        return get_drive_provider(drive_type, **drive_config)
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдера Google Drive: {e}")
        return None

def filter_personal_events(events: List[CalendarEvent]) -> tuple[List[CalendarEvent], List[Dict[str, Any]]]:
    """Фильтровать события для личного аккаунта."""
    filtered_events = []
    excluded_events = []
    
    # Загружаем список исключений из файла
    personal_keywords = load_personal_exclusions()
    
    for event in events:
        # Исключаем события по ключевым словам из файла
        is_excluded = False
        matched_keywords = []
        
        for keyword in personal_keywords:
            if keyword.lower() in event.title.lower():
                is_excluded = True
                matched_keywords.append(keyword)
        
        if is_excluded:
            logger.info(f"⏭️ Исключено событие: {event.title}")
            excluded_events.append({
                'title': event.title,
                'start': event.start,
                'end': event.end,
                'reason': 'Исключено по ключевому слову',
                'keywords': matched_keywords
            })
            continue
        
        # Все остальные события считаем личными
        filtered_events.append(event)
        logger.info(f"✅ Добавлено личное событие: {event.title}")
    
    return filtered_events, excluded_events

def format_personal_folder_name(event: CalendarEvent) -> str:
    """Форматировать название папки для личного аккаунта."""
    start_time = event.start
    title = event.title
    
    # Формат: YYYY-MM-DD hh-mm Название встречи
    folder_name = f"{start_time.strftime('%Y-%m-%d %H-%M')} {title}"
    
    # Очищаем название от недопустимых символов
    folder_name = folder_name.replace('/', '-').replace('\\', '-').replace(':', '-')
    folder_name = folder_name.replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
    
    return folder_name

def create_personal_notion_page(event: CalendarEvent, folder_link: str = "") -> str:
    """Создать страницу в Notion для личного события."""
    try:
        # Загружаем шаблон
        template_path = "templates/meeting_page_template.json"
        if not os.path.exists(template_path):
            logger.error(f"❌ Шаблон не найден: {template_path}")
            return ""
        
        with open(template_path, 'r', encoding='utf-8') as f:
            import json
            template = json.load(f)
        
        # Заполняем шаблон данными события
        template_data = {
            "title": event.title,
            "start_time": event.start.strftime('%H:%M'),
            "end_time": event.end.strftime('%H:%M'),
            "date": event.start.strftime('%Y-%m-%d'),
            "description": event.description,
            "location": event.location,
            "attendees": event.attendees,
            "meeting_link": event.meeting_link,
            "folder_link": folder_link,
            "calendar_source": event.calendar_source
        }
        
        # Создаем страницу в Notion
        notion_token = os.getenv('NOTION_TOKEN')
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not notion_token or not database_id:
            logger.error("❌ Не настроены Notion токен или ID базы данных")
            return ""
        
        page_id = create_page_with_template(
            notion_token, 
            database_id, 
            template, 
            template_data
        )
        
        if page_id:
            logger.info(f"✅ Создана страница в Notion: {page_id}")
            return page_id
        else:
            logger.error("❌ Не удалось создать страницу в Notion")
            return ""
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания страницы в Notion: {e}")
        return ""

def process_personal_event(event: CalendarEvent, drive_provider) -> Dict[str, Any]:
    """Обработать личное событие."""
    try:
        logger.info(f"🔄 Обрабатываю личное событие: {event.title}")
        
        # Форматируем название папки
        folder_name = format_personal_folder_name(event)
        
        # Проверяем существование папки
        if drive_provider and drive_provider.file_exists(folder_name):
            logger.info(f"📁 Папка уже существует: {folder_name}")
            folder_created = False
        else:
            # Создаем папку
            if drive_provider:
                folder_id = drive_provider.create_folder(folder_name)
                if folder_id:
                    logger.info(f"✅ Создана папка: {folder_name}")
                    folder_created = True
                else:
                    logger.error(f"❌ Не удалось создать папку: {folder_name}")
                    folder_created = False
            else:
                logger.warning("⚠️ Провайдер Google Drive недоступен")
                folder_created = False
        
        # Создаем страницу в Notion
        folder_link = f"file://{folder_name}" if folder_created else ""
        notion_page_id = create_personal_notion_page(event, folder_link)
        
        # Формируем результат
        result = {
            'title': event.title,
            'start': event.start,
            'end': event.end,
            'attendees_count': len(event.attendees),
            'has_meeting_link': bool(event.meeting_link),
            'drive_folder_created': folder_created,
            'notion_page_id': notion_page_id,
            'drive_folder_link': folder_link
        }
        
        logger.info(f"✅ Событие обработано: {event.title}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
        return {
            'title': event.title,
            'start': event.start,
            'end': event.end,
            'attendees_count': 0,
            'has_meeting_link': False,
            'drive_folder_created': False,
            'notion_page_id': '',
            'drive_folder_link': '',
            'error': str(e)
        }

def process_personal_calendar_events(days: int = 2) -> Dict[str, Any]:
    """Обработать события личного календаря."""
    try:
        logger.info("📅 Начинаю обработку личного календаря...")
        
        # Получаем провайдер календаря
        calendar_provider = get_personal_calendar_provider()
        if not calendar_provider:
            logger.error("❌ Не удалось получить провайдер календаря")
            return {'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}
        
        # Получаем события на указанное количество дней
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = start_date + timedelta(days=days)
        
        events = calendar_provider.get_events(start_date, end_date)
        logger.info(f"📅 Найдено событий: {len(events)}")
        
        # Фильтруем события
        filtered_events, excluded_events = filter_personal_events(events)
        logger.info(f"✅ Отфильтровано личных событий: {len(filtered_events)}")
        logger.info(f"⏭️ Исключено событий: {len(excluded_events)}")
        
        # Получаем провайдер Google Drive
        drive_provider = get_personal_drive_provider()
        
        # Обрабатываем события
        processed_events = 0
        processed_details = []
        
        for event in filtered_events:
            try:
                result = process_personal_event(event, drive_provider)
                processed_details.append(result)
                processed_events += 1
                
                # Выводим информацию о событии
                logger.info(f"✅ Обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
        
        # Статистика
        excluded_count = len(excluded_events)
        
        result = {
            'processed': processed_events,
            'excluded': excluded_count,
            'errors': len(events) - processed_events - excluded_count,
            'details': processed_details,
            'excluded_details': excluded_events
        }
        
        logger.info(f"📊 Статистика обработки: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
        return {'processed': 0, 'excluded': 0, 'errors': 1, 'details': []}

def process_personal_media_files(quality: str = 'medium') -> Dict[str, Any]:
    """Обработать медиа файлы для личного аккаунта."""
    try:
        logger.info("🎬 Начинаю обработку медиа файлов для личного аккаунта...")
        
        # Получаем провайдер Google Drive
        drive_provider = get_personal_drive_provider()
        if not drive_provider:
            logger.warning("⚠️ Провайдер Google Drive недоступен, пропускаю медиа обработку")
            return {'processed': 0, 'synced': 0, 'cleanup': 0, 'errors': 0, 'details': []}
        
        # Получаем список папок
        folders = drive_provider.list_files()
        personal_folders = [f for f in folders if f.mime_type == 'application/vnd.google-apps.folder']
        
        logger.info(f"📁 Найдено личных папок: {len(personal_folders)}")
        
        # Обрабатываем папки
        total_processed = 0
        total_synced = 0
        total_errors = 0
        media_details = []
        
        for folder in personal_folders[:5]:  # Обрабатываем последние 5 папок
            try:
                folder_name = folder.name
                logger.info(f"🔄 Обрабатываю папку: {folder_name}")
                
                # Инициализируем отслеживание статуса для папки
                folder_path = drive_provider.get_local_path(folder.file_id) if hasattr(drive_provider, 'get_local_path') else None
                if folder_path:
                    processing_status = ProcessingStatus(folder_path)
                    logger.info(f"📊 Отслеживание статуса инициализировано для папки: {folder_path}")
                else:
                    processing_status = None
                    logger.warning(f"⚠️ Не удалось получить локальный путь для папки: {folder_name}")
                
                # Получаем файлы в папке
                folder_files = drive_provider.list_files(folder.file_id)
                
                # Фильтруем видео файлы, исключая уже обработанные
                video_files = [f for f in folder_files if 'video' in f.mime_type and 'compressed' not in f.name.lower()]
                
                # Если есть отслеживание статуса, фильтруем по нему
                if processing_status:
                    original_video_files = video_files.copy()
                    video_files = []
                    for video_file in original_video_files:
                        if not processing_status.is_file_processed(video_file.name, 'video_compression'):
                            video_files.append(video_file)
                            # Добавляем файл в отслеживание, если его там нет
                            if video_file.name not in processing_status.status_data['files']:
                                processing_status.add_file(video_file.local_path, 'video')
                        else:
                            logger.info(f"⏭️ Файл уже обработан (по статусу): {video_file.name}")
                
                if video_files:
                    logger.info(f"🎥 Найдено видео файлов: {len(video_files)}")
                    
                    # Обрабатываем видео файлы
                    folder_processed = 0
                    start_time = time.time()
                    
                    for video_file in video_files:
                        try:
                            logger.info(f"🎬 Обрабатываю видео: {video_file.name}")
                            
                            # Проверяем, не содержит ли название файла слово "compressed"
                            if 'compressed' in video_file.name.lower():
                                logger.info(f"⏭️ Пропускаю уже обработанное видео: {video_file.name}")
                                folder_processed += 1
                                continue
                            
                            # Получаем локальный путь к файлу
                            local_video_path = video_file.local_path
                            if not local_video_path or not os.path.exists(local_video_path):
                                logger.warning(f"⚠️ Локальный путь недоступен: {video_file.name}")
                                continue
                            
                            # Создаем пути для выходных файлов
                            output_dir = Path(local_video_path).parent
                            
                            # 1. Сжатое видео
                            video_output_name = Path(video_file.name).stem + f"_compressed.mp4"
                            video_output_path = output_dir / video_output_name
                            
                            # 2. Аудио файл
                            audio_output_name = Path(video_file.name).stem + f"_compressed.mp3"
                            audio_output_path = output_dir / audio_output_name
                            
                            # Проверяем, не обработаны ли уже файлы
                            if video_output_path.exists() and audio_output_path.exists():
                                logger.info(f"✅ Файлы уже обработаны: {video_output_name}, {audio_output_name}")
                                folder_processed += 1
                                continue
                            
                            # Загружаем настройки видео компрессии из env.personal
                            video_compression = os.getenv('VIDEO_COMPRESSION', 'true').lower() == 'true'
                            video_quality = os.getenv('VIDEO_QUALITY', 'medium')
                            video_codec = os.getenv('VIDEO_CODEC', 'h264')
                            
                            logger.info(f"🎬 Настройки компрессии: compression={video_compression}, quality={video_quality}, codec={video_codec}")
                            
                            # 1. Сжимаем видео (если включено)
                            if video_compression:
                                logger.info(f"🎥 Сжатие видео {video_file.name}...")
                                
                                # Настройки качества для разных уровней
                                if video_quality == 'low':
                                    crf = '28'  # Высокое сжатие
                                    preset = 'ultrafast'
                                elif video_quality == 'medium':
                                    crf = '23'  # Среднее сжатие
                                    preset = 'fast'
                                elif video_quality == 'high':
                                    crf = '18'  # Низкое сжатие
                                    preset = 'medium'
                                else:  # ultra
                                    crf = '15'  # Минимальное сжатие
                                    preset = 'slow'
                                
                                video_cmd = [
                                    'ffmpeg', '-i', local_video_path,
                                    '-c:v', 'libx264' if video_codec == 'h264' else 'libx265',
                                    '-preset', preset,
                                    '-crf', crf,
                                    '-c:a', 'aac',
                                    '-b:a', '128k',
                                    '-movflags', '+faststart',
                                    '-y',
                                    str(video_output_path)
                                ]
                                
                                logger.info(f"🔄 Команда сжатия: {' '.join(video_cmd)}")
                                video_result = subprocess.run(video_cmd, capture_output=True, text=True, timeout=3600)
                                
                                if video_result.returncode == 0:
                                    # Получаем размер сжатого файла
                                    compressed_size = video_output_path.stat().st_size if video_output_path.exists() else 0
                                    original_size = Path(local_video_path).stat().st_size
                                    compression_ratio = original_size / compressed_size if compressed_size > 0 else 0
                                    
                                    logger.info(f"✅ Видео сжато: {video_output_name}")
                                    logger.info(f"📊 Размер: {original_size / (1024**3):.1f} ГБ → {compressed_size / (1024**3):.1f} ГБ (сжатие в {compression_ratio:.1f} раз)")
                                    
                                    # Отмечаем файл как обработанный
                                    if processing_status:
                                        processing_status.mark_file_processed(
                                            video_file.name, 
                                            'video_compression',
                                            [str(video_output_path)]
                                        )
                                else:
                                    logger.error(f"❌ Ошибка сжатия видео: {video_result.stderr}")
                                    if processing_status:
                                        processing_status.mark_file_failed(
                                            video_file.name,
                                            'video_compression',
                                            video_result.stderr
                                        )
                                    video_output_path = None
                            else:
                                logger.info("⏭️ Сжатие видео отключено")
                                video_output_path = None
                            
                            # 2. Конвертируем в аудио
                            logger.info(f"🎵 Конвертация {video_file.name} в mp3...")
                            
                            audio_cmd = [
                                'ffmpeg', '-i', local_video_path,
                                '-vn',  # Без видео
                                '-acodec', 'libmp3lame',
                                '-ab', '192k',  # Среднее качество для личного аккаунта
                                '-y',
                                str(audio_output_path)
                            ]
                            
                            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=1800)
                            
                            if audio_result.returncode == 0:
                                logger.info(f"✅ Аудио создано: {audio_output_name}")
                                folder_processed += 1
                                total_processed += 1
                                
                                # Отмечаем файл как обработанный на этапе аудио
                                if processing_status:
                                    processing_status.mark_file_processed(
                                        video_file.name,
                                        'audio_extraction',
                                        [str(audio_output_path)]
                                    )
                            else:
                                logger.error(f"❌ Ошибка конвертации в аудио: {audio_result.stderr}")
                                
                                # Отмечаем файл как неудачно обработанный на этапе аудио
                                if processing_status:
                                    processing_status.mark_file_failed(
                                        video_file.name,
                                        'audio_extraction',
                                        audio_result.stderr
                                    )
                                
                        except Exception as e:
                            logger.error(f"❌ Ошибка обработки {video_file.name}: {e}")
                    
                    processing_time = time.time() - start_time
                    
                    # Выводим сводку по статусу обработки
                    if processing_status:
                        processing_status.print_summary()
                    
                    media_details.append({
                        "folder": folder_name,
                        "files_found": len(video_files),
                        "files_processed": folder_processed,
                        "processing_time": processing_time
                    })
                    
                    total_synced += len(video_files)
                else:
                    logger.info(f"📁 В папке {folder_name} нет видео файлов")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки папки {folder.name}: {e}")
                total_errors += 1
        
        result = {
            'processed': total_processed,
            'synced': total_synced,
            'cleanup': 0,  # Пока не реализовано
            'errors': total_errors,
            'details': media_details
        }
        
        logger.info(f"📊 Статистика медиа обработки: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка медиа обработки: {e}")
        return {'processed': 0, 'synced': 0, 'cleanup': 0, 'errors': 1, 'details': []}


def process_personal_audio_files(max_folders: int = 5, output_format: str = 'json', cleanup: bool = False) -> Dict[str, Any]:
    """Обработать аудио файлы для личного аккаунта с Whisper."""
    try:
        logger.info("🎤 Начинаю обработку аудио файлов для личного аккаунта...")
        
        # Получаем провайдер Google Drive
        drive_provider = get_personal_drive_provider()
        if not drive_provider:
            logger.warning("⚠️ Провайдер Google Drive недоступен, пропускаю аудио обработку")
            return {'processed': 0, 'transcribed': 0, 'errors': 0, 'details': []}
        
        # Получаем список папок
        folders = drive_provider.list_files()
        personal_folders = [f for f in folders if f.mime_type == 'application/vnd.google-apps.folder']
        
        logger.info(f"📁 Найдено личных папок: {len(personal_folders)}")
        
        # Инициализируем аудио процессор
        try:
            audio_processor = AudioProcessor('env.personal')
            logger.info("✅ Аудио процессор инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации аудио процессора: {e}")
            return {'processed': 0, 'transcribed': 0, 'errors': 1, 'details': []}
        
        # Обрабатываем папки
        total_processed = 0
        total_transcribed = 0
        total_errors = 0
        audio_details = []
        
        for folder in personal_folders[:max_folders]:  # Обрабатываем последние max_folders папок
            try:
                folder_name = folder.name
                logger.info(f"🔄 Обрабатываю папку: {folder_name}")
                
                # Получаем файлы в папке
                folder_files = drive_provider.list_files(folder.file_id)
                audio_files = [f for f in folder_files if 'audio' in f.mime_type or f.name.endswith(('.mp3', '.wav', '.m4a'))]
                
                if audio_files:
                    logger.info(f"🎤 Найдено аудио файлов: {len(audio_files)}")
                    
                    # Обрабатываем аудио файлы
                    folder_processed = 0
                    folder_transcribed = 0
                    start_time = time.time()
                    
                    for audio_file in audio_files:
                        try:
                            logger.info(f"🎤 Обрабатываю аудио: {audio_file.name}")
                            
                            # Получаем локальный путь к файлу
                            local_audio_path = audio_file.local_path
                            if not local_audio_path or not os.path.exists(local_audio_path):
                                logger.warning(f"⚠️ Локальный путь недоступен: {audio_file.name}")
                                continue
                            
                            # Проверяем, не обработан ли уже файл
                            output_dir = Path(local_audio_path).parent
                            transcript_name = Path(audio_file.name).stem + f"_transcript.{output_format}"
                            transcript_path = output_dir / transcript_name
                            
                            if transcript_path.exists():
                                logger.info(f"✅ Транскрипт уже существует: {transcript_name}")
                                folder_processed += 1
                                continue
                            
                            # Обрабатываем аудио с Whisper
                            logger.info(f"🎤 Транскрипция {audio_file.name}...")
                            result = audio_processor.process_audio_file(str(local_audio_path), output_format)
                            
                            if result and result.get('transcription'):
                                folder_processed += 1
                                folder_transcribed += 1
                                logger.info(f"✅ Транскрипция завершена: {len(result['transcription'])} участников")
                            else:
                                logger.warning(f"⚠️ Транскрипция не удалась: {audio_file.name}")
                                
                        except Exception as e:
                            logger.error(f"❌ Ошибка обработки аудио {audio_file.name}: {e}")
                            total_errors += 1
                            continue
                    
                    # Статистика папки
                    processing_time = time.time() - start_time
                    audio_details.append({
                        'folder': folder_name,
                        'files_found': len(audio_files),
                        'files_processed': folder_processed,
                        'files_transcribed': folder_transcribed,
                        'processing_time': processing_time
                    })
                    
                    total_processed += folder_processed
                    total_transcribed += folder_transcribed
                    
                else:
                    logger.info(f"📁 В папке {folder_name} аудио файлов не найдено")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка обработки папки {folder_name}: {e}")
                total_errors += 1
                continue
        
        # Очистка временных файлов если нужно
        if cleanup:
            try:
                audio_processor.cleanup_temp_files()
                logger.info("🧹 Временные аудио файлы очищены")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось очистить временные файлы: {e}")
        
        # Формируем результат
        result = {
            'processed': total_processed,
            'transcribed': total_transcribed,
            'errors': total_errors,
            'details': audio_details
        }
        
        logger.info(f"📊 Статистика аудио обработки: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка аудио обработки: {e}")
        return {'processed': 0, 'transcribed': 0, 'errors': 1, 'details': []}

def create_personal_telegram_report(calendar_stats: Dict[str, Any], media_stats: Dict[str, Any] = None) -> str:
    """Создать отчет для Telegram о работе с личным аккаунтом."""
    try:
        report = "👤 *ОТЧЕТ ЛИЧНОГО АККАУНТА*\n"
        report += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Статистика календаря
        report += "📅 *Календарь:*\n"
        report += f"   ✅ Обработано: {calendar_stats['processed']}\n"
        report += f"   ⏭️ Исключено: {calendar_stats['excluded']}\n"
        report += f"   ❌ Ошибки: {calendar_stats['errors']}\n\n"
        
        # Детали обработанных событий
        if calendar_stats['details']:
            report += "📋 *Обработанные встречи:*\n"
            for detail in calendar_stats['details']:
                start_time = detail['start'].strftime('%H:%M')
                title = detail['title']
                attendees = detail['attendees_count']
                
                report += f"   🕐 {start_time} | {title}\n"
                if attendees > 0:
                    report += f"      👥 Участники: {attendees}\n"
                if detail.get('notion_page_id'):
                    report += f"      📝 Notion: {detail['notion_page_id'][:8]}...\n"
                if detail.get('drive_folder_created'):
                    report += f"      📁 Папка создана\n"
                report += "\n"
        
        # Статистика медиа (если есть)
        if media_stats:
            # Определяем тип статистики
            if 'transcribed' in media_stats:
                # Аудио статистика
                report += "🎤 *Аудио файлы:*\n"
                report += f"   📁 Папок обработано: {len(media_stats['details'])}\n"
                report += f"   📄 Файлов обработано: {media_stats['processed']}\n"
                report += f"   🎤 Транскрипций создано: {media_stats['transcribed']}\n"
                report += f"   ❌ Ошибки: {media_stats['errors']}\n\n"
            else:
                # Медиа статистика
                report += "🎬 *Медиа файлы:*\n"
                report += f"   📁 Папок обработано: {len(media_stats['details'])}\n"
                report += f"   📄 Файлов синхронизировано: {media_stats['synced']}\n"
                report += f"   ❌ Ошибки: {media_stats['errors']}\n\n"
            
            if media_stats['details']:
                report += "📁 *Обработанные папки:*\n"
                for detail in media_stats['details']:
                    report += f"   📂 {detail['folder']}\n"
                    report += f"      🎥 Найдено: {detail['files_found']}\n"
                    if 'files_transcribed' in detail:
                        # Аудио детали
                        report += f"      🎤 Обработано: {detail['files_processed']}\n"
                        report += f"      📝 Транскрипций: {detail['files_transcribed']}\n"
                    else:
                        # Медиа детали
                        report += f"      ✅ Обработано: {detail['files_processed']}\n"
                    report += f"      ⏱️ Время: {detail['processing_time']:.1f}с\n\n"
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания отчета: {e}")
        return f"❌ Ошибка создания отчета: {e}"

def send_personal_telegram_notification(report: str):
    """Отправить уведомление в Telegram для личного аккаунта."""
    try:
        from meeting_automation_personal_only import notify
        
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not bot_token or not chat_id:
            logger.warning("⚠️ Не настроены Telegram параметры")
            return False
        
        # Отправляем уведомление
        success = notify(bot_token, chat_id, report)
        
        if success:
            logger.info("✅ Уведомление отправлено в Telegram")
        else:
            logger.error("❌ Не удалось отправить уведомление")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}")
        return False

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Автоматизация встреч для личного аккаунта')
    parser.add_argument('command', choices=['prepare', 'media', 'audio', 'test'], 
                       help='Команда для выполнения')
    parser.add_argument('--days', type=int, default=2,
                       help='Количество дней для обработки календаря')
    parser.add_argument('--folders', type=int, default=5,
                       help='Максимум папок для обработки')
    parser.add_argument('--cleanup', action='store_true',
                       help='Очистить старые файлы')
    parser.add_argument('--verbose', action='store_true',
                       help='Подробный режим логирования')
    parser.add_argument('--config-only', action='store_true',
                       help='Только проверка конфигурации')
    parser.add_argument('--calendar-only', action='store_true',
                       help='Только проверка календаря')
    parser.add_argument('--drive-only', action='store_true',
                       help='Только проверка Google Drive')
    parser.add_argument('--quality', choices=['low', 'medium', 'high', 'ultra'], default='medium',
                       help='Качество сжатия видео')
    parser.add_argument('--output', choices=['json', 'txt', 'srt'], default='json',
                       help='Формат вывода транскрипта (по умолчанию: json)')
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🔍 Включен подробный режим логирования")
    
    # Загружаем переменные окружения
    if not load_personal_environment():
        logger.error("❌ Не удалось загрузить переменные окружения")
        sys.exit(1)
    
    logger.info("🚀 Запуск автоматизации для личного аккаунта")
    
    if args.command == 'prepare':
        # Обрабатываем календарь
        calendar_stats = process_personal_calendar_events(args.days)
        
        # Создаем отчет
        report = create_personal_telegram_report(calendar_stats)
        
        # Отправляем уведомление только если есть изменения
        if calendar_stats['processed'] > 0:
            send_personal_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'audio':
        # Обрабатываем аудио файлы
        audio_stats = process_personal_audio_files(
            max_folders=args.folders,
            output_format=args.output,
            cleanup=args.cleanup
        )
        
        # Создаем отчет
        report = create_personal_telegram_report({'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}, audio_stats)
        
        # Отправляем уведомление только если есть изменения
        if audio_stats['transcribed'] > 0 or audio_stats['processed'] > 0:
            send_personal_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'media':
        # Обрабатываем медиа файлы
        media_stats = process_personal_media_files(quality=args.quality)
        
        # Создаем отчет
        report = create_personal_telegram_report({'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}, media_stats)
        
        # Отправляем уведомление только если есть изменения
        if media_stats['synced'] > 0 or media_stats['processed'] > 0:
            send_personal_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'test':
        # Тестируем провайдеры
        logger.info("🧪 Тестирование провайдеров для личного аккаунта...")
        
        if args.config_only:
            logger.info("🔧 Проверка только конфигурации...")
            # Проверяем переменные окружения
            required_vars = [
                'GOOGLE_CREDENTIALS', 'PERSONAL_CALENDAR_ID', 'PERSONAL_DRIVE_PARENT_ID',
                'NOTION_TOKEN', 'NOTION_DATABASE_ID', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'
            ]
            for var in required_vars:
                value = os.getenv(var)
                if value:
                    logger.info(f"✅ {var}: {value[:8]}..." if len(value) > 8 else f"✅ {var}: {value}")
                else:
                    logger.error(f"❌ {var}: не установлен")
            return
        
        if args.calendar_only:
            logger.info("📅 Проверка только календаря...")
            calendar_provider = get_personal_calendar_provider()
            if calendar_provider:
                events = calendar_provider.get_today_events()
                logger.info(f"✅ Календарь: найдено {len(events)} событий на сегодня")
            else:
                logger.error("❌ Календарь: провайдер недоступен")
            return
        
        if args.drive_only:
            logger.info("💾 Проверка только Google Drive...")
            drive_provider = get_personal_drive_provider()
            if drive_provider:
                files = drive_provider.list_files()
                logger.info(f"✅ Google Drive: найдено {len(files)} файлов")
            else:
                logger.error("❌ Google Drive: провайдер недоступен")
            return
        
        # Полное тестирование
        # Тест календаря
        calendar_provider = get_personal_calendar_provider()
        if calendar_provider:
            events = calendar_provider.get_today_events()
            logger.info(f"✅ Календарь: найдено {len(events)} событий на сегодня")
        else:
            logger.error("❌ Календарь: провайдер недоступен")
        
        # Тест Google Drive
        drive_provider = get_personal_drive_provider()
        if drive_provider:
            files = drive_provider.list_files()
            logger.info(f"✅ Google Drive: найдено {len(files)} файлов")
        else:
            logger.error("❌ Google Drive: провайдер недоступен")
        
        logger.info("🧪 Тестирование завершено")

if __name__ == "__main__":
    main()
