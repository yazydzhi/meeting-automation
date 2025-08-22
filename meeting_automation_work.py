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

def filter_work_events(events: List[CalendarEvent]) -> List[CalendarEvent]:
    """Фильтровать события для рабочего аккаунта."""
    filtered_events = []
    excluded_keywords = ['День рождения', 'Дела', 'Личное', 'Personal']
    
    for event in events:
        # Исключаем личные события
        if any(keyword.lower() in event.title.lower() for keyword in excluded_keywords):
            logger.info(f"⏭️ Исключено событие: {event.title}")
            continue
        
        # Проверяем, что это рабочее событие
        if any(keyword in event.title.lower() for keyword in ['встреча', 'meeting', 'совещание', 'call']):
            filtered_events.append(event)
            logger.info(f"✅ Добавлено рабочее событие: {event.title}")
        else:
            logger.info(f"⏭️ Пропущено нерабочее событие: {event.title}")
    
    return filtered_events

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
        notion_page_id = create_work_notion_page(event, folder_link)
        
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

def process_work_calendar_events() -> Dict[str, Any]:
    """Обработать события рабочего календаря."""
    try:
        logger.info("📅 Начинаю обработку рабочего календаря...")
        
        # Получаем провайдер календаря
        calendar_provider = get_work_calendar_provider()
        if not calendar_provider:
            logger.error("❌ Не удалось получить провайдер календаря")
            return {'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}
        
        # Получаем события на сегодня и завтра
        today = datetime.now().date()
        start_date = datetime.combine(today, datetime.min.time())
        end_date = start_date + timedelta(days=2)
        
        events = calendar_provider.get_events(start_date, end_date)
        logger.info(f"📅 Найдено событий: {len(events)}")
        
        # Фильтруем события
        filtered_events = filter_work_events(events)
        logger.info(f"✅ Отфильтровано рабочих событий: {len(filtered_events)}")
        
        # Получаем провайдер Google Drive
        drive_provider = get_work_drive_provider()
        
        # Обрабатываем события
        processed_events = 0
        processed_details = []
        
        for event in filtered_events:
            try:
                result = process_work_event(event, drive_provider)
                processed_details.append(result)
                processed_events += 1
                
                # Выводим информацию о событии
                logger.info(f"✅ Обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
        
        # Статистика
        excluded_count = len(events) - len(filtered_events)
        
        result = {
            'processed': processed_events,
            'excluded': excluded_count,
            'errors': len(events) - processed_events - excluded_count,
            'details': processed_details
        }
        
        logger.info(f"📊 Статистика обработки: {result}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
        return {'processed': 0, 'excluded': 0, 'errors': 1, 'details': []}

def process_work_media_files() -> Dict[str, Any]:
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
        
        for folder in work_folders[:5]:  # Обрабатываем последние 5 папок
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
    parser = argparse.ArgumentParser(description='Автоматизация встреч для рабочего аккаунта')
    parser.add_argument('command', choices=['prepare', 'media', 'test'], 
                       help='Команда для выполнения')
    parser.add_argument('--folders', type=int, default=5,
                       help='Максимум папок для обработки')
    parser.add_argument('--cleanup', action='store_true',
                       help='Очистить старые файлы')
    
    args = parser.parse_args()
    
    # Загружаем переменные окружения
    if not load_work_environment():
        logger.error("❌ Не удалось загрузить переменные окружения")
        sys.exit(1)
    
    logger.info("🚀 Запуск автоматизации для рабочего аккаунта")
    
    if args.command == 'prepare':
        # Обрабатываем календарь
        calendar_stats = process_work_calendar_events()
        
        # Создаем отчет
        report = create_work_telegram_report(calendar_stats)
        
        # Отправляем уведомление только если есть изменения
        if calendar_stats['processed'] > 0:
            send_work_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
        # Выводим отчет в консоль
        print(report)
        
    elif args.command == 'media':
        # Обрабатываем медиа файлы
        media_stats = process_work_media_files()
        
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
        
        # Тест календаря
        calendar_provider = get_work_calendar_provider()
        if calendar_provider:
            events = calendar_provider.get_today_events()
            logger.info(f"✅ Календарь: найдено {len(events)} событий на сегодня")
        else:
            logger.error("❌ Календарь: провайдер недоступен")
        
        # Тест Google Drive
        drive_provider = get_work_drive_provider()
        if drive_provider:
            files = drive_provider.list_files()
            logger.info(f"✅ Google Drive: найдено {len(files)} файлов")
        else:
            logger.error("❌ Google Drive: провайдер недоступен")
        
        logger.info("🧪 Тестирование завершено")

if __name__ == "__main__":
    main()
