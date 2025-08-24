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
import time
import subprocess
import json
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
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)

def convert_html_to_readable_text(html_text: str) -> str:
    """Конвертировать HTML текст в читаемый Markdown формат для Notion."""
    import re
    
    if not html_text:
        return ""
    
    # Убираем HTML теги и заменяем их на Markdown
    text = html_text
    
    # Заменяем HTML теги на Markdown
    replacements = [
        # Заголовки
        (r'<h1[^>]*>(.*?)</h1>', r'# \1'),
        (r'<h2[^>]*>(.*?)</h2>', r'## \1'),
        (r'<h3[^>]*>(.*?)</h3>', r'### \1'),
        
        # Жирный текст
        (r'<b[^>]*>(.*?)</b>', r'**\1**'),
        (r'<strong[^>]*>(.*?)</strong>', r'**\1**'),
        
        # Курсив
        (r'<i[^>]*>(.*?)</i>', r'*\1*'),
        (r'<em[^>]*>(.*?)</em>', r'*\1*'),
        
        # Подчеркнутый
        (r'<u[^>]*>(.*?)</u>', r'__\1__'),
        
        # Списки
        (r'<ul[^>]*>(.*?)</ul>', r'\1'),
        (r'<ol[^>]*>(.*?)</ol>', r'\1'),
        (r'<li[^>]*>(.*?)</li>', r'• \1'),
        
        # Ссылки
        (r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>', r'[\2](\1)'),
        
        # Переносы строк
        (r'<br\s*/?>', r'\n'),
        (r'<br>', r'\n'),
        
        # Параграфы
        (r'<p[^>]*>(.*?)</p>', r'\1\n\n'),
        
        # Разделители
        (r'<hr\s*/?>', r'---\n'),
        (r'<hr>', r'---\n'),
        
        # Цитаты
        (r'<blockquote[^>]*>(.*?)</blockquote>', r'> \1'),
        
        # Код
        (r'<code[^>]*>(.*?)</code>', r'`\1`'),
        (r'<pre[^>]*>(.*?)</pre>', r'```\n\1\n```'),
    ]
    
    # Применяем замены
    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE | re.DOTALL)
    
    # Убираем оставшиеся HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Обрабатываем специальные символы
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    
    # Обрабатываем экранированные символы
    text = text.replace('\\n', '\n')
    text = text.replace('\\t', '\t')
    text = text.replace('\\r', '\n')
    
    # Очищаем лишние пробелы и переносы
    text = re.sub(r'\n\s*\n\s*\n', '\n\n', text)  # Убираем лишние пустые строки
    text = re.sub(r' +', ' ', text)  # Убираем лишние пробелы
    text = text.strip()
    
    # Ограничиваем длину текста для Notion (максимум 1800 символов)
    if len(text) > 1800:
        text = text[:1800] + "...\n\n[Текст обрезан из-за ограничений Notion]"
    
    return text

def create_enhanced_meeting_template(
    title: str,
    start_time: datetime,
    end_time: datetime,
    attendees: List[str],
    description: str,
    meeting_links: List[str],
    meeting_link: str,
    folder_link: str,
    location: str
) -> Dict[str, Any]:
    """Создать улучшенный шаблон страницы встречи с детальной информацией."""
    template = {
        "children": []
    }
    
    # Заголовок встречи
    template["children"].append({
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": f"📋 {title}"
                    }
                }
            ]
        }
    })
    
    # Информация о встрече
    template["children"].append({
        "object": "block",
        "type": "heading_2",
        "heading_2": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": "ℹ️ Информация о встрече"
                    }
                }
            ]
        }
    })
    
    # Время встречи
    time_info = f"⏰ {start_time.strftime('%d.%m.%Y %H:%M')} - {end_time.strftime('%H:%M')}"
    template["children"].append({
        "object": "block",
        "type": "callout",
        "callout": {
            "icon": {"emoji": "⏰"},
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": time_info
                    }
                }
            ]
        }
    })
    
    # Место встречи (если есть)
    if location:
        template["children"].append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "📍"},
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📍 {location}"
                        }
                    }
                ]
            }
        })
    
    # Участники
    if attendees:
        template["children"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "👥 Участники"
                        }
                    }
                ]
            }
        })
        
        for attendee in attendees:
            template["children"].append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": attendee
                            }
                        }
                    ]
                }
            })
    
    # Ссылки на встречу
    all_links = []
    if meeting_link:
        all_links.append(meeting_link)
    if meeting_links:
        all_links.extend(meeting_links)
    
    if all_links:
        template["children"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🔗 Ссылки"
                        }
                    }
                ]
            }
        })
        
        for link in all_links:
            content = link
            # Ограничиваем длину ссылки для Notion (максимум 1800 символов)
            if len(content) > 1800:
                content = content[:1800] + "...\n\n[Ссылка обрезана из-за ограничений Notion]"
            
            template["children"].append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        }
                    ]
                }
            })
    
    # Описание встречи
    if description:
        template["children"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📝 Описание"
                        }
                    }
                ]
            }
        })
        
        # Разбиваем описание на параграфы для лучшей читаемости
        paragraphs = description.split('\n\n')
        for paragraph in paragraphs:
            if paragraph.strip():
                # Проверяем, является ли параграф списком
                if paragraph.strip().startswith('•'):
                    # Это список
                    items = paragraph.strip().split('\n')
                    for item in items:
                        if item.strip():
                            content = item.strip()[1:].strip()  # Убираем маркер списка
                            # Ограничиваем длину элемента списка для Notion (максимум 1800 символов)
                            if len(content) > 1800:
                                content = content[:1800] + "...\n\n[Текст обрезан из-за ограничений Notion]"
                            
                            template["children"].append({
                                "object": "block",
                                "type": "bulleted_list_item",
                                "bulleted_list_item": {
                                    "rich_text": [
                                        {
                                            "type": "text",
                                            "text": {
                                                "content": content
                                            }
                                        }
                                    ]
                                }
                            })
                else:
                    # Обычный параграф
                    content = paragraph.strip()
                    # Ограничиваем длину параграфа для Notion (максимум 1800 символов)
                    if len(content) > 1800:
                        content = content[:1800] + "...\n\n[Текст обрезан из-за ограничений Notion]"
                    
                    template["children"].append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": content
                                    }
                                }
                            ]
                        }
                    })
    
    # Папка Google Drive
    if folder_link:
        template["children"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "📁 Файлы встречи"
                        }
                    }
                ]
            }
        })
        
        template["children"].append({
            "object": "block",
            "type": "callout",
            "callout": {
                "icon": {"emoji": "📁"},
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📁 Папка с файлами: {folder_link}"
                        }
                    }
                ]
            }
        })
    
    return template

def should_update_notion_page(event: CalendarEvent, page_id: str) -> bool:
    """Проверить, нужно ли обновить страницу в Notion."""
    try:
        # Пока что всегда возвращаем True для обновления
        # В будущем можно добавить более детальную проверку изменений
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки необходимости обновления: {e}")
        return False

def update_work_notion_page(event: CalendarEvent, page_id: str, folder_link: str) -> bool:
    """Обновить существующую страницу в Notion."""
    try:
        logger.info(f"🔄 Обновление страницы в Notion: {page_id}")
        
        # Обрабатываем участников для отображения ФИО и email
        attendees_info = []
        if event.attendees:
            try:
                from config.employee_database import get_attendees_with_names
                attendees_info = get_attendees_with_names(event.attendees)
            except ImportError:
                # Если база данных недоступна, используем простой формат
                for attendee in event.attendees:
                    if '@' in attendee:
                        # Извлекаем имя из email (убираем домен)
                        name = attendee.split('@')[0]
                        # Заменяем точки на пробелы для лучшей читаемости
                        name = name.replace('.', ' ').replace('_', ' ').title()
                        attendees_info.append(f"{name} ({attendee})")
                    else:
                        attendees_info.append(attendee)
        
        # Обрабатываем описание встречи
        meeting_description = ""
        meeting_links = []
        if event.description:
            import re
            url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
            urls = re.findall(url_pattern, event.description)
            
            for url in urls:
                if 'meet.google.com' in url or 'zoom.us' in url or 'telemost' in url.lower():
                    meeting_links.append(url)
            
            # Конвертируем HTML в читаемый текст
            meeting_description = convert_html_to_readable_text(event.description)
        
        # Создаем обновленный шаблон
        updated_template = create_enhanced_meeting_template(
            event.title,
            event.start,
            event.end,
            attendees_info,
            meeting_description,
            meeting_links,
            event.meeting_link,
            folder_link,
            event.location
        )
        
        # Обновляем страницу через API Notion
        notion_token = os.getenv('NOTION_TOKEN')
        if not notion_token:
            logger.error("❌ Не настроен NOTION_TOKEN")
            return False
        
        # Сначала очищаем существующее содержимое
        if clear_notion_page_content(notion_token, page_id):
            # Затем добавляем новое содержимое
            if apply_notion_template(notion_token, page_id, updated_template):
                logger.info(f"✅ Страница успешно обновлена: {page_id}")
                return True
            else:
                logger.error(f"❌ Не удалось применить обновленный шаблон: {page_id}")
                return False
        else:
            logger.error(f"❌ Не удалось очистить содержимое страницы: {page_id}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка обновления страницы в Notion: {e}")
        return False

def clear_notion_page_content(notion_token: str, page_id: str) -> bool:
    """Очистить содержимое страницы в Notion."""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Получаем список блоков страницы
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"❌ Не удалось получить блоки страницы: {response.status_code}")
            return False
        
        blocks = response.json().get("results", [])
        
        # Удаляем все блоки (кроме первого - заголовка)
        for block in blocks[1:]:
            delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code != 200:
                logger.warning(f"⚠️ Не удалось удалить блок {block['id']}: {delete_response.status_code}")
        
        logger.info(f"✅ Содержимое страницы очищено: {page_id}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки содержимого страницы: {e}")
        return False

def apply_notion_template(notion_token: str, page_id: str, template: Dict[str, Any]) -> bool:
    """Применить шаблон к странице в Notion."""
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Добавляем блоки шаблона к странице
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        
        response = requests.patch(url, headers=headers, json=template)
        
        if response.status_code == 200:
            logger.info(f"✅ Шаблон успешно применен к странице: {page_id}")
            return True
        else:
            logger.error(f"❌ Ошибка применения шаблона: {response.status_code}")
            logger.error(f"   Тело ответа: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Ошибка применения шаблона: {e}")
        return False

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
        
        # Обрабатываем участников для отображения ФИО и email
        attendees_info = []
        if event.attendees:
            try:
                from config.employee_database import get_attendees_with_names
                attendees_info = get_attendees_with_names(event.attendees)
            except ImportError:
                # Если база данных недоступна, используем простой формат
                for attendee in event.attendees:
                    if '@' in attendee:
                        # Пытаемся извлечь имя из email
                        name = attendee.split('@')[0]
                        attendees_info.append(f"{name} ({attendee})")
                    else:
                        attendees_info.append(attendee)
        
        # Обрабатываем описание встречи
        meeting_description = ""
        meeting_links = []
        if event.description:
            # Ищем ссылки в описании
            import re
            url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+'
            urls = re.findall(url_pattern, event.description)
            
            for url in urls:
                if 'meet.google.com' in url or 'zoom.us' in url or 'telemost' in url.lower():
                    meeting_links.append(url)
            
            # Убираем ссылки из описания для основного текста
            clean_description = re.sub(url_pattern, '', event.description).strip()
            meeting_description = clean_description
        
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
        
        # Добавляем участников с ФИО и email
        if event.attendees and "Attendees" in schema:
            page_properties["Attendees"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": ", ".join(attendees_info) if attendees_info else ", ".join(event.attendees)
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
        
        # Создаем улучшенный шаблон с детальной информацией о встрече
        enhanced_template = create_enhanced_meeting_template(
            event.title,
            event.start,
            event.end,
            attendees_info,
            meeting_description,
            meeting_links,
            event.meeting_link,
            folder_link,
            event.location
        )
        
        page_id = create_page_with_template(
            notion_token, 
            database_id, 
            page_properties,  # properties
            enhanced_template  # enhanced template
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
        notion_page_updated = False
        if notion_token and database_id:
            existing_page_id = check_notion_page_exists(notion_token, database_id, event_id)
            if existing_page_id:
                notion_page_id = existing_page_id
                logger.info(f"📄 Используем существующую страницу в Notion: {notion_page_id}")
                
                # Проверяем, нужно ли обновить страницу (если изменились данные)
                if should_update_notion_page(event, existing_page_id):
                    logger.info(f"🔄 Обновляю страницу в Notion: {existing_page_id}")
                    update_success = update_work_notion_page(event, existing_page_id, folder_link)
                    notion_page_updated = update_success
                    if update_success:
                        logger.info(f"✅ Страница обновлена: {existing_page_id}")
                    else:
                        logger.warning(f"⚠️ Не удалось обновить страницу: {existing_page_id}")
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
            'notion_page_created': notion_page_created,
            'notion_page_updated': notion_page_updated,  # Новое поле
            'drive_folder_link': folder_link,
            'event_id': event_id
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
                            audio_output_name = Path(video_file.name).stem + f"_compressed.{output_format}"
                            audio_output_path = output_dir / audio_output_name
                            
                            # Проверяем, не обработаны ли уже файлы
                            if video_output_path.exists() and audio_output_path.exists():
                                logger.info(f"✅ Файлы уже обработаны: {video_output_name}, {audio_output_name}")
                                folder_processed += 1
                                continue
                            
                            # Загружаем настройки видео компрессии из env.work
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
                                else:
                                    logger.error(f"❌ Ошибка сжатия видео: {video_result.stderr}")
                                    video_output_path = None
                            else:
                                logger.info("⏭️ Сжатие видео отключено")
                                video_output_path = None
                            
                            # 2. Конвертируем в аудио
                            logger.info(f"🎵 Конвертация {video_file.name} в {output_format}...")
                            
                            audio_cmd = [
                                'ffmpeg', '-i', local_video_path,
                                '-vn',  # Без видео
                                '-acodec', 'libmp3lame' if output_format == 'mp3' else 'pcm_s16le',
                                '-ab', '128k' if quality == 'low' else '192k' if quality == 'medium' else '320k',
                                '-y',
                                str(audio_output_path)
                            ]
                            
                            audio_result = subprocess.run(audio_cmd, capture_output=True, text=True, timeout=1800)
                            
                            if audio_result.returncode == 0:
                                logger.info(f"✅ Аудио создано: {audio_output_name}")
                                folder_processed += 1
                                total_processed += 1
                            else:
                                logger.error(f"❌ Ошибка конвертации в аудио: {audio_result.stderr}")
                                
                        except Exception as e:
                            logger.error(f"❌ Ошибка обработки {video_file.name}: {e}")
                    
                    processing_time = time.time() - start_time
                    
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

def format_time(seconds: float) -> str:
    """Форматирует время в формат SRT (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds % 1) * 1000)
    seconds = int(seconds)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def process_work_audio_files(max_folders: int = 5, output_format: str = 'json', cleanup: bool = False, use_advanced_segmentation: bool = True, segmentation_method: str = 'energy') -> Dict[str, Any]:
    """Обработать аудио файлы для рабочего аккаунта с Whisper и продвинутой сегментацией."""
    try:
        logger.info("🎤 Начинаю обработку аудио файлов для рабочего аккаунта...")
        
        # Получаем провайдер Google Drive
        drive_provider = get_work_drive_provider()
        if not drive_provider:
            logger.warning("⚠️ Провайдер Google Drive недоступен, пропускаю аудио обработку")
            return {'processed': 0, 'transcribed': 0, 'errors': 0, 'details': []}
        
        # Получаем список папок
        folders = drive_provider.list_files()
        work_folders = [f for f in folders if f.mime_type == 'application/vnd.google-apps.folder']
        
        logger.info(f"📁 Найдено рабочих папок: {len(work_folders)}")
        
        # Инициализируем аудио процессор
        try:
            audio_processor = AudioProcessor('env.work')
            logger.info("✅ Аудио процессор инициализирован")
            
            # Проверяем доступность продвинутой сегментации
            if use_advanced_segmentation:
                try:
                    from advanced_segmentation import AdvancedSegmentation
                    logger.info(f"🚀 Продвинутая сегментация доступна - используем метод: {segmentation_method}")
                except ImportError:
                    logger.warning("⚠️ Продвинутая сегментация недоступна - используем стандартный метод")
                    use_advanced_segmentation = False
                    segmentation_method = 'standard'
            else:
                segmentation_method = 'standard'
                
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации аудио процессора: {e}")
            return {'processed': 0, 'transcribed': 0, 'errors': 1, 'details': []}
        
        # Обрабатываем папки
        total_processed = 0
        total_transcribed = 0
        total_errors = 0
        audio_details = []
        
        for folder in work_folders[:max_folders]:  # Обрабатываем последние max_folders папок
            try:
                folder_name = folder.name
                logger.info(f"🔄 Обрабатываю папку: {folder_name}")
                
                # Получаем файлы в папке
                folder_files = drive_provider.list_files(folder.file_id)
                audio_files = [f for f in folder_files if (
                    'audio' in f.mime_type or 
                    f.name.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg'))
                )]
                
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
                            
                            # Обрабатываем аудио с Whisper и продвинутой сегментацией
                            logger.info(f"🎤 Транскрипция {audio_file.name} с методом: {segmentation_method}...")
                            
                            if use_advanced_segmentation and segmentation_method in ['energy', 'adaptive', 'intonation', 'emotion']:
                                # Используем продвинутую сегментацию
                                result = audio_processor.process_audio_file_with_advanced_segmentation(
                                    str(local_audio_path), 
                                    segmentation_method
                                )
                                logger.info(f"⚡ Использована {segmentation_method} сегментация")
                            else:
                                # Используем метод без сегментации
                                result = audio_processor.process_audio_file_full(str(local_audio_path), output_format)
                                logger.info(f"📝 Использован метод без сегментации")
                            
                            if result and result.get('raw_transcriptions'):
                                folder_processed += 1
                                folder_transcribed += 1
                                
                                # Сохраняем результат в нужном формате
                                if output_format == 'json':
                                    with open(transcript_path, 'w', encoding='utf-8') as f:
                                        import json
                                        json.dump(result, f, ensure_ascii=False, indent=2)
                                elif output_format == 'txt':
                                    with open(transcript_path, 'w', encoding='utf-8') as f:
                                        f.write(f"ТРАНСКРИПЦИЯ: {audio_file.name}\n")
                                        f.write(f"Время обработки: {result.get('processed_at', '')}\n")
                                        f.write(f"Сегментов: {result.get('total_segments', 0)}\n")
                                        f.write(f"Спикеров: {len(result.get('speakers', {}))}\n")
                                        f.write("-" * 50 + "\n\n")
                                        
                                        for trans in result.get('raw_transcriptions', []):
                                            f.write(f"[{trans.get('start_time', 0)}ms - {trans.get('end_time', 0)}ms] ")
                                            f.write(f"Сегмент {trans.get('segment', '?')}\n")
                                            f.write(f"{trans.get('text', '')}\n\n")
                                elif output_format == 'srt':
                                    with open(transcript_path, 'w', encoding='utf-8') as f:
                                        for i, trans in enumerate(result.get('raw_transcriptions', []), 1):
                                            start_time_s = trans.get('start_time', 0) / 1000
                                            end_time_s = trans.get('end_time', 0) / 1000
                                            f.write(f"{i}\n")
                                            f.write(f"{format_time(start_time_s)} --> {format_time(end_time_s)}\n")
                                            f.write(f"{trans.get('text', '')}\n\n")
                                
                                logger.info(f"✅ Транскрипция завершена: {len(result.get('raw_transcriptions', []))} сегментов, {len(result.get('speakers', {}))} участников")
                                logger.info(f"💾 Результат сохранен: {transcript_path}")
                                
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
                        'processing_time': processing_time,
                        'segmentation_method': segmentation_method
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
    parser.add_argument('command', choices=['prepare', 'media', 'audio', 'test', 'watch', 'analyze'], 
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
    
    # Параметры для команды audio
    parser.add_argument('--output', choices=['json', 'txt', 'srt'], default='json',
                       help='Формат вывода транскрипта (по умолчанию: json)')
    parser.add_argument('--segmentation', choices=['standard', 'energy', 'adaptive'], default='energy',
                       help='Метод сегментации (по умолчанию: energy)')
    parser.add_argument('--no-advanced', action='store_true',
                       help='Отключить продвинутую сегментацию')
    
    # Параметры для команды watch
    parser.add_argument('--interval', type=int, default=300,
                       help='Интервал проверки в секундах (по умолчанию: 300)')
    
    # Параметры для команды analyze
    parser.add_argument('--transcript', type=str, required=False,
                       help='Путь к файлу транскрипции для анализа')
    parser.add_argument('--title', type=str, default='',
                       help='Название встречи для анализа')
    parser.add_argument('--date', type=str, default='',
                       help='Дата встречи для анализа')
    
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
        
    elif args.command == 'audio':
        # Обрабатываем аудио файлы
        use_advanced = not args.no_advanced
        segmentation_method = args.segmentation if use_advanced else 'standard'
        
        logger.info(f"🎤 Запуск обработки аудио с сегментацией: {segmentation_method}")
        
        audio_stats = process_work_audio_files(
            max_folders=args.folders,
            output_format=args.output,
            cleanup=args.cleanup,
            use_advanced_segmentation=use_advanced,
            segmentation_method=segmentation_method
        )
        
        # Создаем отчет
        report = create_work_telegram_report({'processed': 0, 'excluded': 0, 'errors': 0, 'details': []}, audio_stats)
        
        # Отправляем уведомление только если есть изменения
        if audio_stats['transcribed'] > 0 or audio_stats['processed'] > 0:
            send_work_telegram_notification(report)
            logger.info("📱 Уведомление отправлено (есть изменения)")
        else:
            logger.info("📱 Уведомление не отправлено (изменений нет)")
        
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
        
    elif args.command == 'analyze':
        # Анализируем транскрипцию и создаем страницу в Notion
        if not args.transcript:
            logger.error("❌ Необходимо указать путь к файлу транскрипции (--transcript)")
            sys.exit(1)
        
        if not os.path.exists(args.transcript):
            logger.error(f"❌ Файл транскрипции не найден: {args.transcript}")
            sys.exit(1)
        
        logger.info(f"🔍 Анализ транскрипции: {args.transcript}")
        logger.info(f"📋 Название встречи: {args.title or 'Не указано'}")
        logger.info(f"📅 Дата встречи: {args.date or 'Не указана'}")
        
        # Анализируем транскрипцию
        analysis_result = analyze_transcript_and_create_notion_page(
            args.transcript,
            args.title,
            args.date
        )
        
        if analysis_result['success']:
            logger.info("✅ Анализ транскрипции завершен успешно")
            logger.info(f"📊 Файл анализа: {analysis_result['analysis_file']}")
            logger.info(f"📋 Данные для Notion: {analysis_result['notion_data_file']}")
            
            # Создаем отчет
            summary = analysis_result['analysis_result'].get('meeting_summary', {})
            report = f"""
🔍 АНАЛИЗ ТРАНСКРИПЦИИ ЗАВЕРШЕН

📋 Встреча: {summary.get('title', 'Не указано')}
🎯 Тема: {summary.get('main_topic', 'Не указано')}
✅ Решения: {len(summary.get('key_decisions', []))}
📋 Действия: {len(summary.get('action_items', []))}
💬 Темы: {len(analysis_result['analysis_result'].get('topics_discussed', []))}
⏰ Сроки: {len(analysis_result['analysis_result'].get('deadlines', []))}

💾 Файлы созданы:
   - Анализ: {os.path.basename(analysis_result['analysis_file'])}
   - Данные для Notion: {os.path.basename(analysis_result['notion_data_file'])}

📋 Страница готова для создания в Notion
"""
            print(report)
            
            # Отправляем уведомление в Telegram
            send_work_telegram_notification(report)
            logger.info("📱 Уведомление отправлено в Telegram")
            
        else:
            logger.error(f"❌ Ошибка анализа: {analysis_result.get('error', 'Неизвестная ошибка')}")
            sys.exit(1)
        
    else:
        logger.error(f"❌ Неизвестная команда: {args.command}")
        sys.exit(1)

def analyze_transcript_and_create_notion_page(
    transcript_file_path: str,
    meeting_title: str = "",
    meeting_date: str = ""
) -> Dict[str, Any]:
    """
    Анализирует транскрипцию через OpenAI и создает страницу в Notion
    
    Args:
        transcript_file_path: Путь к файлу транскрипции
        meeting_title: Название встречи
        meeting_date: Дата встречи
        
    Returns:
        Словарь с результатами анализа и создания страницы
    """
    try:
        logger.info(f"🔍 Анализирую транскрипцию: {transcript_file_path}")
        
        # Читаем транскрипцию
        with open(transcript_file_path, 'r', encoding='utf-8') as f:
            transcript_text = f.read()
        
        logger.info(f"📝 Прочитана транскрипция: {len(transcript_text)} символов")
        
        # Загружаем конфигурацию
        config_manager = ConfigManager('env.work')
        openai_config = config_manager.config.get('openai', {})
        
        api_key = openai_config.get('api_key')
        if not api_key:
            raise ValueError("OPENAI_API_KEY не найден в конфигурации")
        
        model = openai_config.get('analysis_model', 'gpt-4o-mini')
        
        # Создаем анализатор
        from src.transcript_analyzer import TranscriptAnalyzer
        analyzer = TranscriptAnalyzer(api_key, model)
        
        # Анализируем транскрипцию
        logger.info("🔍 Начинаю анализ через OpenAI...")
        analysis_result = analyzer.analyze_meeting_transcript(
            transcript_text,
            meeting_title,
            meeting_date
        )
        
        logger.info("✅ Анализ завершен успешно")
        
        # Сохраняем результат анализа
        analysis_file = transcript_file_path.replace('.txt', '_analysis.json')
        if analyzer.save_analysis_to_file(analysis_result, analysis_file):
            logger.info(f"💾 Результат анализа сохранен: {analysis_file}")
        
        # Создаем данные для Notion
        logger.info("📝 Создаю данные для страницы Notion...")
        notion_page_data = analyzer.create_notion_page_data(analysis_result)
        
        if not notion_page_data:
            raise ValueError("Не удалось создать данные для Notion")
        
        # Сохраняем данные для Notion
        notion_data_file = transcript_file_path.replace('.txt', '_notion_data.json')
        with open(notion_data_file, 'w', encoding='utf-8') as f:
            json.dump(notion_page_data, f, ensure_ascii=False, indent=2)
        logger.info(f"💾 Данные для Notion сохранены: {notion_data_file}")
        
        # TODO: Здесь будет интеграция с Notion API для создания страницы
        logger.info("📋 Данные готовы для создания страницы в Notion")
        
        return {
            'success': True,
            'analysis_file': analysis_file,
            'notion_data_file': notion_data_file,
            'analysis_result': analysis_result,
            'notion_page_data': notion_page_data
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка анализа транскрипции: {e}")
        return {
            'success': False,
            'error': str(e)
        }

if __name__ == "__main__":
    main()
