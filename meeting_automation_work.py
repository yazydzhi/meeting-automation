#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт автоматизации встреч для РАБОЧЕГО аккаунта
Использует альтернативные провайдеры для обхода корпоративных ограничений
"""

import os
import sys
import argparse
import logging
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
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

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

def notify(bot_token: str, chat_id: str, text: str) -> bool:
    """Отправить уведомление в Telegram."""
    try:
        import requests
        r = requests.get(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            params={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, 
            timeout=15
        )
        r.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления в Telegram: {e}")
        return False

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/work_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_work_environment():
    """Загрузить переменные окружения для рабочего аккаунта."""
    try:
        # Пытаемся загрузить конфигурацию рабочего аккаунта
        if os.path.exists('env.work'):
            from dotenv import load_dotenv
            load_dotenv('env.work')
            logger.info("✅ Загружена конфигурация рабочего аккаунта")
        else:
            logger.warning("⚠️ Файл env.work не найден, используем .env")
            from dotenv import load_dotenv
            load_dotenv()
        
        # Проверяем обязательные переменные
        required_vars = [
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

def get_work_calendar_provider():
    """Получить провайдер календаря для рабочего аккаунта."""
    try:
        config = ConfigManager('env.work' if os.path.exists('env.work') else '.env')
        calendar_type = config.get_calendar_provider_type()
        calendar_config = config.get_calendar_provider_config()
        
        logger.info(f"📅 Используем провайдер календаря: {calendar_type}")
        
        if calendar_type == 'google_api':
            # Для рабочего аккаунта Google API может быть заблокирован
            logger.warning("⚠️ Google API может быть заблокирован для рабочего аккаунта")
            return get_calendar_provider(calendar_type, **calendar_config)
        else:
            # Альтернативные провайдеры
            return get_calendar_provider(calendar_type, **calendar_config)
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдера календаря: {e}")
        return None

def get_work_drive_provider():
    """Получить провайдер Google Drive для рабочего аккаунта."""
    try:
        config = ConfigManager('env.work' if os.path.exists('env.work') else '.env')
        drive_type = config.get_drive_provider_type()
        drive_config = config.get_drive_provider_config()
        
        logger.info(f"💾 Используем провайдер Google Drive: {drive_type}")
        
        if drive_type == 'google_api':
            # Для рабочего аккаунта Google API может быть заблокирован
            logger.warning("⚠️ Google API может быть заблокирован для рабочего аккаунта")
            return get_drive_provider(drive_type, **drive_config)
        else:
            # Альтернативные провайдеры
            return get_drive_provider(drive_type, **drive_config)
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения провайдера Google Drive: {e}")
        return None

def filter_work_events(events: List[CalendarEvent]) -> tuple[List[CalendarEvent], List[Dict[str, Any]]]:
    """Фильтровать события для рабочего аккаунта."""
    filtered_events = []
    excluded_events = []
    
    # Загружаем список исключений из файла
    personal_keywords = load_personal_exclusions()
    
    for event in events:
        # Исключаем только личные события по ключевым словам
        is_personal = False
        matched_keywords = []
        
        for keyword in personal_keywords:
            if keyword.lower() in event.title.lower():
                is_personal = True
                matched_keywords.append(keyword)
        
        if is_personal:
            logger.info(f"⏭️ Исключено личное событие: {event.title}")
            excluded_events.append({
                'title': event.title,
                'start': event.start,
                'end': event.end,
                'reason': 'Личное событие',
                'keywords': matched_keywords
            })
            continue
        
        # Все остальные события считаем рабочими
        filtered_events.append(event)
        logger.info(f"✅ Добавлено рабочее событие: {event.title}")
    
    return filtered_events, excluded_events

def format_work_folder_name(event: CalendarEvent) -> str:
    """Форматировать название папки для рабочего аккаунта."""
    start_time = event.start
    title = event.title
    
    # Формат: YYYY-MM-DD hh-mm Название встречи
    folder_name = f"{start_time.strftime('%Y-%m-%d %H-%M')} {title}"
    
    # Очищаем название от недопустимых символов
    folder_name = folder_name.replace('/', '-').replace('\\', '-').replace(':', '-')
    folder_name = folder_name.replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
    
    return folder_name

def check_notion_page_exists(notion_token: str, database_id: str, event_id: str) -> str:
    """Проверить, существует ли страница с данным Event ID в Notion."""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        
        # Поиск страницы по Event ID
        filter_data = {
            "filter": {
                "property": "Event ID",
                "rich_text": {
                    "equals": event_id
                }
            }
        }
        
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json=filter_data
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            if results:
                page_id = results[0]['id']
                logger.info(f"✅ Найдена существующая страница: {page_id}")
                return page_id
            else:
                logger.info(f"🔍 Страница с Event ID '{event_id}' не найдена")
                return ""
        else:
            logger.error(f"❌ Ошибка поиска страницы: {response.status_code}")
            return ""
            
    except Exception as e:
        logger.error(f"❌ Ошибка проверки существования страницы: {e}")
        return ""

def get_notion_database_schema(notion_token: str, database_id: str) -> Dict[str, Any]:
    """Получить схему базы данных Notion."""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
        }
        
        response = requests.get(
            f"https://api.notion.com/v1/databases/{database_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            properties = data.get('properties', {})
            logger.info(f"🔍 Схема базы данных Notion:")
            for prop_name, prop_data in properties.items():
                prop_type = prop_data.get('type', 'unknown')
                logger.info(f"   📝 {prop_name}: {prop_type}")
            return properties
        else:
            logger.error(f"❌ Ошибка получения схемы базы данных: {response.status_code}")
            logger.error(f"   Тело ответа: {response.text}")
            return {}
            
    except Exception as e:
        logger.error(f"❌ Ошибка получения схемы базы данных: {e}")
        return {}

def create_work_notion_page(event: CalendarEvent, folder_link: str = "") -> str:
    """Создать страницу в Notion для рабочего события."""
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
        
        if not notion_token:
            logger.error("❌ Не настроен NOTION_TOKEN")
            return ""
        
        if not database_id:
            logger.error("❌ Не настроен NOTION_DATABASE_ID")
            return ""
        
        logger.info(f"🔧 Создание страницы в Notion для: {event.title}")
        logger.info(f"   📅 Дата: {event.start.strftime('%Y-%m-%d %H:%M')}")
        logger.info(f"   🗄️ База данных: {database_id[:8]}...")
        logger.info(f"   🔑 Токен: {notion_token[:8]}...")
        
        # Создаем Event ID для проверки
        import hashlib
        event_hash = hashlib.md5(f"{event.start.isoformat()}{event.title}".encode()).hexdigest()[:8]
        event_id = f"work_{event_hash}"
        
        # Проверяем, существует ли уже страница с таким Event ID
        existing_page_id = check_notion_page_exists(notion_token, database_id, event_id)
        if existing_page_id:
            logger.info(f"⏭️ Страница уже существует, пропускаем создание")
            return existing_page_id
        
        # Получаем схему базы данных
        schema = get_notion_database_schema(notion_token, database_id)
        
        # Создаем свойства страницы для Notion (только обязательные)
        page_properties = {
            "Name": {  # Обязательное свойство
                "title": [
                    {
                        "text": {
                            "content": event.title
                        }
                    }
                ]
            },
            "Date": {  # Обязательное свойство
                "date": {
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat()
                }
            }
        }
        
        # Добавляем пометку о рабочем календаре
        if "Calendar" in schema:
            page_properties["Calendar"] = {
                "select": {
                    "name": "Work"
                }
            }
        
        # Добавляем участников
        if event.attendees and "Attendees" in schema:
            page_properties["Attendees"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": ", ".join(event.attendees)
                        }
                    }
                ]
            }
        
        # Добавляем ссылку на встречу
        if event.meeting_link and "Meeting Link" in schema:
            page_properties["Meeting Link"] = {
                "url": event.meeting_link
            }
        
        # Добавляем папку Google Drive
        if folder_link and "Drive Folder" in schema:
            page_properties["Drive Folder"] = {
                "url": folder_link
            }
        
        # Добавляем ID события
        if "Event ID" in schema:
            page_properties["Event ID"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": event_id
                        }
                    }
                ]
            }
        
        logger.info(f"🔧 Свойства страницы: {list(page_properties.keys())}")
        
        page_id = create_page_with_template(
            notion_token, 
            database_id, 
            page_properties,  # properties
            template          # template
        )
        
        if page_id:
            logger.info(f"✅ Создана страница в Notion: {page_id}")
            return page_id
        else:
            logger.error("❌ Не удалось создать страницу в Notion (функция вернула None)")
            return ""
            
    except Exception as e:
        logger.error(f"❌ Ошибка создания страницы в Notion: {e}")
        logger.error(f"   📍 Тип ошибки: {type(e).__name__}")
        logger.error(f"   📝 Детали: {str(e)}")
        return ""

def process_work_event(event: CalendarEvent, drive_provider) -> Dict[str, Any]:
    """Обработать рабочее событие."""
    try:
        logger.info(f"🔄 Обрабатываю рабочее событие: {event.title}")
        
        # Форматируем название папки
        folder_name = format_work_folder_name(event)
        
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
        
        # Создаем Event ID для проверки
        import hashlib
        event_hash = hashlib.md5(f"{event.start.isoformat()}{event.title}".encode()).hexdigest()[:8]
        event_id = f"work_{event_hash}"
        
        # Проверяем, существует ли страница
        notion_token = os.getenv('NOTION_TOKEN')
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        notion_page_created = False
        if notion_token and database_id:
            existing_page_id = check_notion_page_exists(notion_token, database_id, event_id)
            if existing_page_id:
                notion_page_id = existing_page_id
                logger.info(f"📄 Используем существующую страницу в Notion: {notion_page_id}")
            else:
                notion_page_id = create_work_notion_page(event, folder_link)
                notion_page_created = bool(notion_page_id)
                if notion_page_created:
                    logger.info(f"✨ Создана новая страница в Notion: {notion_page_id}")
        else:
            notion_page_id = ""
            logger.warning("⚠️ Notion не настроен")
        
        # Формируем результат
        result = {
            'title': event.title,
            'start': event.start,
            'end': event.end,
            'attendees_count': len(event.attendees),
            'has_meeting_link': bool(event.meeting_link),
            'drive_folder_created': folder_created,
            'notion_page_id': notion_page_id,
            'notion_page_created': notion_page_created,  # Новое поле
            'drive_folder_link': folder_link,
            'event_id': event_id  # Новое поле
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

def process_work_calendar_events(days: int = 2, force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Обработать события рабочего календаря."""
    try:
        logger.info("📅 Начинаю обработку рабочего календаря...")
        if dry_run:
            logger.info("🧪 РЕЖИМ ПРОБНОГО ЗАПУСКА - изменения не будут сохранены")
        
        # Получаем провайдер календаря
        calendar_provider = get_work_calendar_provider()
        if not calendar_provider:
            logger.error("❌ Не удалось получить провайдер календаря")
            return {'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}
        
        # Получаем события на сегодня и завтра
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = start_date + timedelta(days=days)
        
        events = calendar_provider.get_events(start_date, end_date)
        logger.info(f"📅 Найдено событий: {len(events)}")
        
        # Показываем все события для диагностики
        logger.info("🔍 Все события из календаря:")
        for i, event in enumerate(events, 1):
            start_time = event.start.strftime('%Y-%m-%d %H:%M')
            end_time = event.end.strftime('%H:%M')
            logger.info(f"   {i}. {start_time}-{end_time} | {event.title}")
        
        # Фильтруем события
        filtered_events, excluded_events = filter_work_events(events)
        logger.info(f"✅ Отфильтровано рабочих событий: {len(filtered_events)}")
        logger.info(f"⏭️ Исключено событий: {len(excluded_events)}")
        
        # Получаем провайдер Google Drive
        drive_provider = get_work_drive_provider()
        
        # Обрабатываем события
        processed_events = 0
        new_events_count = 0  # Счетчик новых событий
        processed_details = []
        
        for event in filtered_events:
            try:
                if dry_run:
                    # В режиме dry-run только показываем, что будет обработано
                    logger.info(f"🧪 [DRY-RUN] Будет обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                    
                    # Создаем заглушку результата
                    result = {
                        'title': event.title,
                        'start': event.start,
                        'end': event.end,
                        'attendees_count': len(event.attendees),
                        'has_meeting_link': bool(event.meeting_link),
                        'drive_folder_created': False,
                        'notion_page_id': '',
                        'notion_page_created': True,  # В dry-run считаем как новое
                        'drive_folder_link': '',
                        'event_id': f"dry_run_{event.title[:8]}"
                    }
                    processed_details.append(result)
                    processed_events += 1
                    new_events_count += 1  # В dry-run все события считаем новыми
                else:
                    # Обычная обработка
                    result = process_work_event(event, drive_provider)
                    processed_details.append(result)
                    processed_events += 1
                    
                    # Проверяем, было ли создано что-то новое
                    if result.get('notion_page_created', False) or result.get('drive_folder_created', False):
                        new_events_count += 1
                    
                    # Выводим информацию о событии
                    status = "✨ Создано" if result.get('notion_page_created', False) else "📄 Существует"
                    logger.info(f"{status}: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
        
        # Статистика
        excluded_count = len(excluded_events)
        
        result = {
            'processed': processed_events,
            'excluded': excluded_count,
            'errors': len(events) - processed_events - excluded_count,
            'new_events': new_events_count,  # Добавляем счетчик новых событий
            'details': processed_details,
            'excluded_details': excluded_events  # Добавляем детали исключенных событий
        }
        
        if dry_run:
            logger.info(f"🧪 [DRY-RUN] Статистика обработки: {result}")
        else:
            logger.info(f"📊 Статистика обработки: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
        return {'processed': 0, 'excluded': 0, 'errors': 1, 'details': []}

def process_work_media_files(max_folders: int = 5, output_format: str = 'mp3', quality: str = 'medium', cleanup: bool = False) -> Dict[str, Any]:
    """Обработать медиа файлы для рабочего аккаунта."""
    try:
        logger.info("🎬 Начинаю обработку медиа файлов для рабочего аккаунта...")
        
        # Получаем провайдер Google Drive
        drive_provider = get_work_drive_provider()
        if not drive_provider:
            logger.warning("⚠️ Провайдер Google Drive недоступен, пропускаю медиа обработку")
            return {'processed': 0, 'synced': 0, 'cleanup': 0, 'errors': 0, 'details': []}
        
        # Получаем список папок
        folders = drive_provider.list_files()
        work_folders = [f for f in folders if f.mime_type == 'application/vnd.google-apps.folder']
        
        logger.info(f"📁 Найдено рабочих папок: {len(work_folders)}")
        
        # Обрабатываем папки
        total_processed = 0
        total_synced = 0
        total_errors = 0
        media_details = []
        
        for folder in work_folders[:max_folders]:  # Обрабатываем последние max_folders папок
            try:
                folder_name = folder.name
                logger.info(f"🔄 Обрабатываю папку: {folder_name}")
                
                # Получаем файлы в папке
                folder_files = drive_provider.list_files(folder.file_id)
                video_files = [f for f in folder_files if 'video' in f.mime_type]
                
                if video_files:
                    logger.info(f"🎥 Найдено видео файлов: {len(video_files)}")
                    
                    # Здесь можно добавить обработку видео файлов
                    # Для рабочего аккаунта можно использовать локальную обработку
                    
                    media_details.append({
                        "folder": folder_name,
                        "files_found": len(video_files),
                        "files_processed": 0,  # Пока не реализовано
                        "processing_time": 0
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

def create_work_telegram_report(calendar_stats: Dict[str, Any], media_stats: Dict[str, Any] = None) -> str:
    """Создать отчет для Telegram о работе с рабочим аккаунтом."""
    try:
        report = "🏢 *ОТЧЕТ РАБОЧЕГО АККАУНТА*\n"
        report += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Статистика календаря
        report += "📅 *Календарь:*\n"
        report += f"   ✅ Обработано: {calendar_stats['processed']}\n"
        report += f"   ✨ Новых: {calendar_stats.get('new_events', 0)}\n"
        report += f"   ⏭️ Исключено: {calendar_stats['excluded']}\n"
        report += f"   ❌ Ошибки: {calendar_stats['errors']}\n\n"
        
        # Детали обработанных событий
        if calendar_stats['details']:
            report += "📋 *Обработанные встречи:*\n"
            for detail in calendar_stats['details']:
                start_time = detail['start'].strftime('%H:%M')
                title = detail['title']
                attendees = detail['attendees_count']
                
                # Показываем статус события
                status_icon = "✨" if detail.get('notion_page_created', False) else "📄"
                report += f"   {status_icon} {start_time} | {title}\n"
                
                if attendees > 0:
                    report += f"      👥 Участники: {attendees}\n"
                if detail.get('notion_page_id'):
                    report += f"      📝 Notion: {detail['notion_page_id'][:8]}...\n"
                if detail.get('drive_folder_created'):
                    report += f"      📁 Папка создана\n"
                if detail.get('notion_page_created'):
                    report += f"      ✨ Новая страница\n"
                if detail.get('event_id'):
                    report += f"      🆔 ID: {detail['event_id']}\n"
                if detail.get('error'):
                    report += f"      ❌ Ошибка: {detail['error']}\n"
                report += "\n"
        
        # Детали исключенных событий
        if calendar_stats.get('excluded_details'):
            report += "⏭️ *Исключенные события:*\n"
            for detail in calendar_stats['excluded_details']:
                start_time = detail['start'].strftime('%H:%M')
                title = detail['title']
                reason = detail['reason']
                
                report += f"   🕐 {start_time} | {title}\n"
                report += f"      📝 Причина: {reason}\n"
                if detail.get('keywords'):
                    report += f"      🔑 Ключевые слова: {', '.join(detail['keywords'])}\n"
                report += "\n"
        
        # Статистика медиа (если есть)
        if media_stats:
            report += "🎬 *Медиа файлы:*\n"
            report += f"   📁 Папок обработано: {len(media_stats['details'])}\n"
            report += f"   📄 Файлов синхронизировано: {media_stats['synced']}\n"
            report += f"   ❌ Ошибки: {media_stats['errors']}\n\n"
            
            if media_stats['details']:
                report += "📁 *Обработанные папки:*\n"
                for detail in media_stats['details']:
                    report += f"   📂 {detail['folder']}\n"
                    report += f"      🎥 Найдено: {detail['files_found']}\n"
                    report += f"      ✅ Обработано: {detail['files_processed']}\n"
                    report += f"      ⏱️ Время: {detail['processing_time']:.1f}с\n\n"
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания отчета: {e}")
        return f"❌ Ошибка создания отчета: {e}"

def send_work_telegram_notification(report: str):
    """Отправить уведомление в Telegram для рабочего аккаунта."""
    try:
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
    parser = argparse.ArgumentParser(description='Автоматизация встреч для рабочего аккаунта')
    parser.add_argument('command', choices=['prepare', 'media', 'test', 'watch'], 
                       help='Команда для выполнения')
    
    # Общие параметры
    parser.add_argument('--folders', type=int, default=5,
                       help='Максимум папок для обработки')
    parser.add_argument('--cleanup', action='store_true',
                       help='Очистить старые файлы')
    parser.add_argument('--verbose', action='store_true',
                       help='Подробный вывод')
    parser.add_argument('--days', type=int, default=2,
                       help='Количество дней для обработки (по умолчанию: 2)')
    
    # Параметры для команды test
    parser.add_argument('--config-only', action='store_true',
                       help='Только проверка конфигурации')
    parser.add_argument('--calendar-only', action='store_true',
                       help='Только тест календаря')
    parser.add_argument('--drive-only', action='store_true',
                       help='Только тест Google Drive')
    
    # Параметры для команды prepare
    parser.add_argument('--force', action='store_true',
                       help='Принудительная обработка всех событий')
    parser.add_argument('--dry-run', action='store_true',
                       help='Пробный запуск без изменений')
    
    # Параметры для команды media
    parser.add_argument('--format', choices=['mp3', 'mp4', 'wav'], default='mp3',
                       help='Формат выходного аудио/видео')
    parser.add_argument('--quality', choices=['low', 'medium', 'high', 'ultra'], default='medium',
                       help='Качество обработки медиа')
    
    # Параметры для команды watch
    parser.add_argument('--interval', type=int, default=300,
                       help='Интервал проверки в секундах (по умолчанию: 300)')
    
    args = parser.parse_args()
    
    # Настройка логирования в зависимости от verbose
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.info("🔍 Включен подробный режим логирования")
    
    # Загружаем переменные окружения
    if not load_work_environment():
        logger.error("❌ Не удалось загрузить переменные окружения")
        sys.exit(1)
    
    logger.info("🚀 Запуск автоматизации для рабочего аккаунта")
    
    if args.command == 'prepare':
        # Обрабатываем календарь
        calendar_stats = process_work_calendar_events(days=args.days, force=args.force, dry_run=args.dry_run)
        
        # Создаем отчет
        report = create_work_telegram_report(calendar_stats)
        
        # Отправляем уведомление только если есть НОВЫЕ события
        if calendar_stats.get('new_events', 0) > 0:
            send_work_telegram_notification(report)
            logger.info(f"📱 Уведомление отправлено (новых событий: {calendar_stats['new_events']})")
        else:
            logger.info(f"📱 Уведомление не отправлено (новых событий нет, обработано: {calendar_stats['processed']})")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'media':
        # Обрабатываем медиа файлы
        media_stats = process_work_media_files(
            max_folders=args.folders,
            output_format=args.format,
            quality=args.quality,
            cleanup=args.cleanup
        )
        
        # Создаем отчет
        report = create_work_telegram_report({'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}, media_stats)
        
        # Отправляем уведомление только если есть изменения
        if media_stats['synced'] > 0 or media_stats['processed'] > 0:
            send_work_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'test':
        # Тестируем провайдеры
        logger.info("🧪 Тестирование провайдеров для рабочего аккаунта...")
        
        # Проверка конфигурации
        if args.config_only:
            logger.info("🔧 Проверка конфигурации...")
            config = ConfigManager('env.work' if os.path.exists('env.work') else '.env')
            print("📋 Конфигурация:")
            print(config.get_config_summary())
            print(f"✅ Валидность: {config.validate_config()}")
            return
        
        # Тест календаря
        if not args.drive_only:
            logger.info("📅 Тестирование календаря...")
            calendar_provider = get_work_calendar_provider()
            if calendar_provider:
                events = calendar_provider.get_today_events()
                logger.info(f"✅ Календарь: найдено {len(events)} событий на сегодня")
                if args.verbose and events:
                    for event in events[:3]:
                        logger.info(f"   - {event.title} ({event.start.strftime('%H:%M')})")
            else:
                logger.error("❌ Календарь: провайдер недоступен")
        
        # Тест Google Drive
        if not args.calendar_only:
            logger.info("💾 Тестирование Google Drive...")
            drive_provider = get_work_drive_provider()
            if drive_provider:
                files = drive_provider.list_files()
                logger.info(f"✅ Google Drive: найдено {len(files)} файлов")
                if args.verbose and files:
                    for file in files[:3]:
                        logger.info(f"   - {file.name} ({file.mime_type})")
            else:
                logger.error("❌ Google Drive: провайдер недоступен")
        
        logger.info("🧪 Тестирование завершено")
        
    elif args.command == 'watch':
        # Режим наблюдения за новыми событиями
        logger.info(f"👀 Запуск режима наблюдения за новыми событиями...")
        logger.info(f"⏰ Интервал проверки: {args.interval} секунд")
        logger.info("⚠️ Режим наблюдения пока не реализован для рабочего аккаунта")
        logger.info("💡 Используйте команду 'prepare' для обработки событий")
        
        # Здесь можно добавить логику наблюдения
        # Например, периодический запуск prepare команды
        # import time
        # while True:
        #     process_work_calendar_events(days=args.days)
        #     time.sleep(args.interval)
        
    else:
        logger.error(f"❌ Неизвестная команда: {args.command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
