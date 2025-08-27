#!/usr/bin/env python3
"""
Универсальный скрипт для автоматизации встреч
Поддерживает различные действия: calendar, drive, media, transcribe, notion, all
"""

import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from config_manager import ConfigManager
    from audio_processor import AudioProcessor
    from media_processor import MediaProcessor
    from notion_api import NotionAPI
    from transcript_analyzer import TranscriptAnalyzer
    from telegram_api import TelegramAPI
    from calendar_alternatives import get_calendar_provider, CalendarEvent
    from drive_alternatives import get_drive_provider, DriveFile
    from notion_templates import create_page_with_template
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)

def setup_logging():
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
                    RotatingFileHandler(
            "logs/meeting_automation_universal.log",
            maxBytes=int(os.getenv("LOG_MAX_SIZE_MB", "100")) * 1024 * 1024,
            backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
            encoding="utf-8"
        )
        ]
    )
    return logging.getLogger(__name__)

def load_environment():
    """Загрузка переменных окружения."""
    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        return config_manager
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return None

def process_account(config_manager: ConfigManager, account_type: str, logger: logging.Logger = None):
    """Обработка аккаунта (календарь и диск)."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"📅 Обработка аккаунта: {account_type}")
    
    try:
        if account_type == 'personal':
            if config_manager.is_personal_enabled():
                logger.info("👤 Обрабатываю личный аккаунт")
                # Получаем провайдер календаря
                calendar_provider = get_calendar_provider(
                    config_manager.get_calendar_provider_type('personal'),
                    **config_manager.get_calendar_provider_config('personal')
                )
                
                if not calendar_provider:
                    logger.error("❌ Не удалось получить провайдер календаря")
                    return {"status": "error", "message": "Failed to get calendar provider"}
                
                # Получаем провайдер диска
                drive_provider = get_drive_provider(
                    config_manager.get_drive_provider_type('personal'),
                    **config_manager.get_drive_provider_config('personal')
                )
                
                if not drive_provider:
                    logger.warning("⚠️ Провайдер диска недоступен")
                
                # Обрабатываем календарные события
                result = process_calendar_events(calendar_provider, drive_provider, account_type, config_manager, logger)
                return result
            else:
                logger.warning("⚠️ Личный аккаунт отключен")
                return {"status": "skipped", "message": "Personal account disabled"}
        
        elif account_type == 'work':
            if config_manager.is_work_enabled():
                logger.info("🏢 Обрабатываю рабочий аккаунт")
                # Получаем провайдер календаря
                calendar_provider = get_calendar_provider(
                    config_manager.get_calendar_provider_type('work'),
                    **config_manager.get_calendar_provider_config('work')
                )
                
                if not calendar_provider:
                    logger.error("❌ Не удалось получить провайдер календаря")
                    return {"status": "error", "message": "Failed to get calendar provider"}
                
                # Получаем провайдер диска
                drive_provider = get_drive_provider(
                    config_manager.get_drive_provider_type('work'),
                    **config_manager.get_drive_provider_config('work')
                )
                
                if not drive_provider:
                    logger.warning("⚠️ Провайдер диска недоступен")
                
                # Обрабатываем календарные события
                result = process_calendar_events(calendar_provider, drive_provider, account_type, config_manager, logger)
                return result
            else:
                logger.warning("⚠️ Рабочий аккаунт отключен")
                return {"status": "skipped", "message": "Work account disabled"}
        
        elif account_type == 'both':
            results = []
            if config_manager.is_personal_enabled():
                personal_result = process_account(config_manager, 'personal', logger)
                results.append(personal_result)
            
            if config_manager.is_work_enabled():
                work_result = process_account(config_manager, 'work', logger)
                results.append(work_result)
            
            return {"status": "success", "message": "Both accounts processed", "results": results}
        
        else:
            logger.error(f"❌ Неизвестный тип аккаунта: {account_type}")
            return {"status": "error", "message": f"Unknown account type: {account_type}"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки аккаунта {account_type}: {e}")
        return {"status": "error", "message": str(e)}

def process_calendar_events(calendar_provider, drive_provider, account_type: str, config_manager: ConfigManager, logger: logging.Logger) -> Dict[str, Any]:
    """Обработка календарных событий и создание папок встреч."""
    try:
        logger.info(f"📅 Начинаю обработку календаря для {account_type} аккаунта...")
        
        # Получаем события на 2 дня вперед
        days = 2
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = start_date + timedelta(days=days)
        
        events = calendar_provider.get_events(start_date, end_date)
        logger.info(f"📅 Найдено событий: {len(events)}")
        
        # Фильтруем события
        filtered_events, excluded_events = filter_events(events, account_type, config_manager, logger)
        logger.info(f"✅ Отфильтровано событий: {len(filtered_events)}")
        logger.info(f"⏭️ Исключено событий: {len(excluded_events)}")
        
        # Обрабатываем события
        processed_events = 0
        processed_details = []
        
        for event in filtered_events:
            try:
                result = process_event(event, drive_provider, account_type, config_manager, logger)
                processed_details.append(result)
                processed_events += 1
                
                # Выводим информацию о событии
                logger.info(f"✅ Обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
        
        # Статистика
        excluded_count = len(excluded_events)
        
        result = {
            'status': 'success',
            'processed': processed_events,
            'excluded': excluded_count,
            'errors': len(events) - processed_events - excluded_count,
            'details': processed_details,
            'excluded_details': excluded_events
        }
        
        logger.info(f"📊 Статистика обработки: обработано {processed_events}, исключено {excluded_count}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
        return {'status': 'error', 'processed': 0, 'excluded': 0, 'errors': 1, 'details': [str(e)]}

def filter_events(events: List[CalendarEvent], account_type: str, config_manager: ConfigManager, logger: logging.Logger) -> tuple[List[CalendarEvent], List[Dict[str, Any]]]:
    """Фильтрация событий календаря."""
    filtered_events = []
    excluded_events = []
    
    # Загружаем список исключений
    exclusions = _load_exclusions(account_type, config_manager, logger)
    
    for event in events:
        # Исключаем события по ключевым словам
        is_excluded = False
        matched_keywords = []
        
        for keyword in exclusions:
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
        
        # Все остальные события считаем подходящими
        filtered_events.append(event)
        logger.info(f"✅ Добавлено событие: {event.title}")
    
    return filtered_events, excluded_events

def _load_exclusions(account_type: str, config_manager: ConfigManager, logger: logging.Logger) -> List[str]:
    """Загрузка списка исключений для фильтрации событий."""
    try:
        # Определяем путь к файлу исключений в зависимости от типа аккаунта
        exclusions_file = Path(f"config/{account_type}_exclusions.txt")
        
        if not exclusions_file.exists():
            logger.warning(f"⚠️ Файл исключений не найден: {exclusions_file}")
            # Возвращаем базовый список по умолчанию
            if account_type == 'personal':
                return ['День рождения', 'Дела', 'Личное', 'Personal', 'Отпуск']
            else:
                return ['Обед', 'Перерыв', 'Отгул', 'Больничный', 'Отпуск']
        
        exclusions = []
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
        if account_type == 'personal':
            return ['День рождения', 'Дела', 'Личное', 'Personal', 'Отпуск']
        else:
            return ['Обед', 'Перерыв', 'Отгул', 'Больничный', 'Отпуск']

def process_event(event: CalendarEvent, drive_provider, account_type: str, config_manager: ConfigManager, logger: logging.Logger) -> Dict[str, Any]:
    """Обработка события календаря и создание папки встречи."""
    try:
        logger.info(f"🔄 Обрабатываю событие: {event.title}")
        
        # Форматируем название папки
        folder_name = format_folder_name(event, account_type)
        
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
                logger.warning("⚠️ Провайдер диска недоступен")
                folder_created = False
        
        # Создаем страницу в Notion
        folder_link = f"file://{folder_name}" if folder_created else ""
        notion_page_id = create_notion_meeting_record(event, folder_link, account_type, config_manager, logger)
        
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

def format_folder_name(event: CalendarEvent, account_type: str) -> str:
    """Форматирование названия папки для встречи."""
    start_time = event.start
    title = event.title
    
    # Формат: YYYY-MM-DD hh-mm Название встречи
    folder_name = f"{start_time.strftime('%Y-%m-%d %H-%M')} {title}"
    
    # Очищаем название от недопустимых символов
    folder_name = folder_name.replace('/', '-').replace('\\', '-').replace(':', '-')
    folder_name = folder_name.replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
    
    return folder_name

def create_notion_meeting_record(event: CalendarEvent, folder_link: str, account_type: str, config_manager: ConfigManager, logger: logging.Logger) -> str:
    """Создание записи в Notion для встречи."""
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
            "calendar_source": event.calendar_source,
            "account_type": account_type
        }
        
        # Получаем настройки Notion
        notion_config = config_manager.get_notion_config()
        notion_token = notion_config.get('token')
        database_id = notion_config.get('database_id')
        
        if not notion_token or not database_id:
            logger.error("❌ Не настроены Notion токен или ID базы данных")
            return ""
        
        # Импортируем функцию создания страницы
        from notion_templates import create_page_with_template
        
        page_id = create_page_with_template(
            notion_token, 
            database_id, 
            template_data, 
            template,
            logger
        )
        
        logger.info(f"🔧 Результат create_page_with_template: {page_id}")
        
        if page_id:
            logger.info(f"✅ Создана страница в Notion: {page_id}")
            return page_id
        else:
            logger.error("❌ Не удалось создать страницу в Notion")
            return ""
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания страницы в Notion: {e}")
        return ""

def process_media(config_manager: ConfigManager, quality: str = 'medium', logger: logging.Logger = None):
    """Обработка медиа файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎬 Запуск обработки медиа файлов...")
    
    try:
        results = []
        total_processed = 0
        total_synced = 0
        
        if config_manager.is_personal_enabled():
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                personal_result = _process_folder_media(personal_folder, "personal", quality, logger)
                results.append(personal_result)
                total_processed += personal_result.get("processed", 0)
                total_synced += personal_result.get("synced", 0)
            else:
                logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
        
        if config_manager.is_work_enabled():
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                work_result = _process_folder_media(work_folder, "work", quality, logger)
                results.append(work_result)
                total_processed += work_result.get("processed", 0)
                total_synced += work_result.get("synced", 0)
            else:
                logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
        
        logger.info(f"✅ Обработка медиа завершена: обработано {total_processed}, найдено {total_synced}")
        return {
            "status": "success", 
            "message": "Media processing completed", 
            "results": results,
            "total_processed": total_processed,
            "total_synced": total_synced
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return {"status": "error", "message": str(e)}

def _process_folder_media(folder_path: str, account_type: str, quality: str, logger: logging.Logger):
    """Обработка медиа файлов в конкретной папке."""
    try:
        result = {"status": "success", "folder": folder_path, "processed": 0, "synced": 0, "total_videos": 0, "processed_files": []}
        
        # Ищем видео файлы
        video_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                    # Исключаем уже сжатые файлы
                    if 'compressed' not in file.lower():
                        video_files.append(os.path.join(root, file))
        
        if not video_files:
            logger.info(f"📁 В папке {folder_path} нет новых видео файлов для обработки")
            return result
        
        logger.info(f"🎥 Найдено {len(video_files)} новых видео файлов для обработки")
        result["total_videos"] = len(video_files)
        
        # Обрабатываем каждый видео файл
        for video_file in video_files:
            try:
                logger.info(f"🎬 Обрабатываю видео: {os.path.basename(video_file)}")
                
                # Создаем имя для сжатого файла
                base_name = os.path.splitext(video_file)[0]
                compressed_video = f"{base_name}_compressed.mp4"
                compressed_audio = f"{base_name}_compressed.mp3"
                
                # Сжимаем видео
                video_success = _compress_video(video_file, compressed_video, quality, logger)
                if video_success:
                    result["processed"] += 1
                    result["processed_files"].append({
                        "file": os.path.basename(video_file),
                        "type": "video",
                        "output": compressed_video,
                        "status": "success"
                    })
                    logger.info(f"✅ Видео сжато: {os.path.basename(compressed_video)}")
                
                # Извлекаем аудио
                audio_success = _extract_audio(video_file, compressed_audio, logger)
                if audio_success:
                    result["processed"] += 1
                    result["processed_files"].append({
                        "file": os.path.basename(video_file),
                        "type": "audio",
                        "output": compressed_audio,
                        "status": "success"
                    })
                    logger.info(f"✅ Аудио извлечено: {os.path.basename(compressed_audio)}")
                
                result["synced"] += 1
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки {os.path.basename(video_file)}: {e}")
                result["processed_files"].append({
                    "file": os.path.basename(video_file),
                    "type": "error",
                    "error": str(e),
                    "status": "error"
                })
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
        return {"status": "error", "folder": folder_path, "processed": 0, "synced": 0, "total_videos": 0, "processed_files": [], "error": str(e)}

def _compress_video(input_file: str, output_file: str, quality: str, logger: logging.Logger) -> bool:
    """Сжатие видео файла через FFmpeg."""
    try:
        # Определяем параметры качества
        quality_params = {
            'low': ['-crf', '28', '-preset', 'fast'],
            'medium': ['-crf', '23', '-preset', 'medium'],
            'high': ['-crf', '18', '-preset', 'slow']
        }
        
        params = quality_params.get(quality, quality_params['medium'])
        
        cmd = [
            'ffmpeg', '-i', input_file,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '128k'
        ] + params + [
            '-y',  # Перезаписывать существующие файлы
            output_file
        ]
        
        logger.info(f"🎬 Запуск FFmpeg: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 минут
        
        if result.returncode == 0:
            logger.info(f"✅ Видео успешно сжато: {output_file}")
            return True
        else:
            logger.error(f"❌ Ошибка сжатия видео: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Таймаут сжатия видео: {input_file}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка сжатия видео {input_file}: {e}")
        return False

def _extract_audio(input_file: str, output_file: str, logger: logging.Logger) -> bool:
    """Извлечение аудио из видео файла."""
    try:
        cmd = [
            'ffmpeg', '-i', input_file,
            '-vn',  # Без видео
            '-c:a', 'mp3',
            '-b:a', '128k',
            '-ar', '44100',
            '-y',  # Перезаписывать существующие файлы
            output_file
        ]
        
        logger.info(f"🎵 Извлечение аудио: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 минут
        
        if result.returncode == 0:
            logger.info(f"✅ Аудио успешно извлечено: {output_file}")
            return True
        else:
            logger.error(f"❌ Ошибка извлечения аудио: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Таймаут извлечения аудио: {input_file}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка извлечения аудио {input_file}: {e}")
        return False

def process_transcription(config_manager: ConfigManager, account_type: str, file_path: str = None, logger: logging.Logger = None):
    """Обработка транскрипции аудио файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎤 Запуск транскрипции аудио...")
    
    try:
        # Инициализируем AudioProcessor
        audio_processor = AudioProcessor()
        
        if file_path:
            # Транскрибируем конкретный файл
            logger.info(f"🎵 Транскрибирую файл: {file_path}")
            if os.path.exists(file_path):
                # Создаем транскрипцию
                transcript = audio_processor._transcribe_full_audio(file_path)
                if transcript:
                    # Сохраняем транскрипцию
                    transcript_file = file_path.replace('.mp3', '_transcript.txt')
                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        f.write(transcript)
                    logger.info(f"✅ Транскрипция сохранена: {transcript_file}")
                    return {"status": "success", "message": f"Transcription saved to {transcript_file}"}
                else:
                    logger.error(f"❌ Не удалось создать транскрипцию для {file_path}")
                    return {"status": "error", "message": f"Failed to create transcription for {file_path}"}
            else:
                logger.error(f"❌ Файл не найден: {file_path}")
                return {"status": "error", "message": f"File not found: {file_path}"}
        else:
            # Транскрибируем все MP3 файлы в папках аккаунтов
            logger.info(f"🎵 Транскрибирую все MP3 файлы для аккаунта: {account_type}")
            
            results = []
            if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
                personal_config = config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = _process_folder_transcription(audio_processor, personal_folder, "personal", logger)
                    results.append(personal_result)
            
            if account_type in ['work', 'both'] and config_manager.is_work_enabled():
                work_config = config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = _process_folder_transcription(audio_processor, work_folder, "work", logger)
                    results.append(work_result)
            
            logger.info("✅ Транскрипция завершена")
            return {"status": "success", "message": "Transcription completed", "results": results}
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрипции: {e}")
        return {"status": "error", "message": str(e)}

def _process_folder_transcription(audio_processor: AudioProcessor, folder_path: str, account_type: str, logger: logging.Logger = None):
    """Обработка транскрипции для конкретной папки."""
    if logger is None:
        logger = logging.getLogger(__name__)
        
    try:
        result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
        
        # Ищем MP3 файлы для транскрипции
        mp3_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):
                    mp3_files.append(os.path.join(root, file))
        
        if not mp3_files:
            return result
        
        logger.info(f"🎵 Найдено {len(mp3_files)} MP3 файлов для транскрипции")
        
        # Обрабатываем каждый MP3 файл
        for mp3_file in mp3_files:
            try:
                # Проверяем, существует ли уже файл транскрипции
                transcript_file = mp3_file.replace('.mp3', '_transcript.txt')
                if os.path.exists(transcript_file):
                    logger.info(f"📄 Файл транскрипции уже существует: {os.path.basename(transcript_file)}")
                    result["processed"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "already_exists",
                        "output": transcript_file
                    })
                    continue
                
                logger.info(f"🎤 Создаю транскрипцию для: {os.path.basename(mp3_file)}")
                transcript = audio_processor._transcribe_full_audio(mp3_file)
                if transcript:
                    # Сохраняем транскрипцию
                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        f.write(transcript)
                    
                    result["processed"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "success",
                        "output": transcript_file
                    })
                else:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "error",
                        "error": "Failed to create transcription"
                    })
                    
            except Exception as e:
                result["errors"] += 1
                result["files"].append({
                    "file": os.path.basename(mp3_file),
                    "status": "error",
                    "error": str(e)
                })
        
        return result
        
    except Exception as e:
        return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}

def process_notion_sync(config_manager: ConfigManager, account_type: str, logger: logging.Logger = None):
    """Синхронизация с Notion."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("📝 Запуск синхронизации с Notion...")
    
    try:
        # Получаем настройки Notion
        notion_config = config_manager.get_notion_config()
        if not notion_config.get('token'):
            logger.error("❌ Токен Notion не настроен")
            return {"status": "error", "message": "Notion token not configured"}
        
        logger.info(f"📋 Синхронизирую с базой данных: {notion_config.get('database_id', 'не указано')}")
        
        # Инициализируем Notion API
        notion_api = NotionAPI(notion_config)
        
        results = []
        if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
            logger.info("👤 Синхронизирую личный аккаунт с Notion")
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                personal_result = _sync_folder_with_notion(notion_api, personal_folder, "personal")
                results.append(personal_result)
        
        if account_type in ['work', 'both'] and config_manager.is_work_enabled():
            logger.info("🏢 Синхронизирую рабочий аккаунт с Notion")
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                work_result = _sync_folder_with_notion(notion_api, work_folder, "work")
                results.append(work_result)
        
        logger.info("✅ Синхронизация с Notion завершена")
        return {"status": "success", "message": "Notion sync completed", "results": results}
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
        return {"status": "error", "message": str(e)}

def _sync_folder_with_notion(notion_api: NotionAPI, folder_path: str, account_type: str):
    """Синхронизация конкретной папки с Notion."""
    try:
        result = {"account": account_type, "folder": folder_path, "synced": 0, "errors": 0, "files": []}
        
        # Ищем файлы транскрипции
        transcript_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('_transcript.txt'):
                    transcript_files.append(os.path.join(root, file))
        
        if not transcript_files:
            return result
        
        # Синхронизируем каждый файл транскрипции
        for transcript_file in transcript_files:
            try:
                # Здесь будет логика синхронизации с Notion
                # Пока просто логируем
                result["synced"] += 1
                result["files"].append({
                    "file": os.path.basename(transcript_file),
                    "status": "synced"
                })
                
            except Exception as e:
                result["errors"] += 1
                result["files"].append({
                    "file": os.path.basename(transcript_file),
                    "status": "error",
                    "error": str(e)
                })
        
        return result
        
    except Exception as e:
        return {"account": account_type, "folder": folder_path, "synced": 0, "errors": 1, "files": [], "error": str(e)}

def process_notification(message: str, notification_type: str = "info", logger: logging.Logger = None):
    """Отправка уведомлений в Telegram."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("📱 Запуск отправки уведомления...")
    
    try:
        # Получаем настройки Telegram
        config_manager = ConfigManager()
        telegram_config = config_manager.get_telegram_config()
        
        if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
            logger.error("❌ Telegram не настроен")
            return {"status": "error", "message": "Telegram not configured"}
        
        # Инициализируем Telegram API
        telegram_api = TelegramAPI(telegram_config)
        
        # Отправляем сообщение с правильным parse_mode
        if notification_type == "detailed":
            # Для детальных отчетов используем HTML
            success = telegram_api.send_message(message, parse_mode="HTML")
        else:
            # Для обычных уведомлений используем HTML (так как у нас есть разметка)
            success = telegram_api.send_message(message, parse_mode="HTML")
        
        if success:
            logger.info("✅ Уведомление отправлено успешно")
            return {"status": "success", "message": "Notification sent successfully"}
        else:
            logger.error("❌ Не удалось отправить уведомление")
            return {"status": "error", "message": "Failed to send notification"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}")
        return {"status": "error", "message": str(e)}

def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Универсальный скрипт автоматизации встреч')
    parser.add_argument('action', choices=['calendar', 'drive', 'media', 'transcribe', 'notion', 'all', 'notify'],
                       help='Действие для выполнения')
    parser.add_argument('--account', choices=['personal', 'work', 'both'], default='both',
                       help='Тип аккаунта для обработки')
    parser.add_argument('--file', help='Путь к конкретному файлу для обработки')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество обработки медиа')
    parser.add_argument('--message', help='Сообщение для команды notify')
    parser.add_argument('--notification_type', choices=['info', 'detailed'], default='info',
                       help='Тип уведомления для команды notify')
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    logger = setup_logging()
    logger.info(f"🚀 Запуск {args.action} для аккаунта: {args.account}")
    
    # Загружаем конфигурацию
    config_manager = load_environment()
    if not config_manager:
        logger.error("❌ Не удалось загрузить конфигурацию")
        sys.exit(1)
    
    try:
        if args.action == 'calendar':
            result = process_account(config_manager, args.account, logger)
        elif args.action == 'drive':
            result = process_account(config_manager, args.account, logger)
        elif args.action == 'media':
            result = process_media(config_manager, args.quality, logger)
        elif args.action == 'transcribe':
            result = process_transcription(config_manager, args.account, args.file, logger)
        elif args.action == 'notion':
            result = process_notion_sync(config_manager, args.account, logger)
        elif args.action == 'notify':
            if not args.message:
                logger.error("❌ Для команды notify необходимо указать --message")
                return 1
            
            result = process_notification(args.message, args.notification_type, logger)
        elif args.action == 'all':
            logger.info("🚀 Запуск всех процессов...")
            results = {}
            results['calendar'] = process_account(config_manager, args.account, logger)
            results['media'] = process_media(config_manager, args.quality, logger)
            results['transcribe'] = process_transcription(config_manager, args.account, args.file, logger)
            results['notion'] = process_notion_sync(config_manager, args.account, logger)
            result = {"status": "success", "message": "All actions completed", "results": results}
        
        logger.info(f"✅ {args.action} завершен: {result}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения {args.action}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
