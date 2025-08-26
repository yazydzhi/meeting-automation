#!/usr/bin/env python3
"""
Модуль для работы с календарем и создания папок встреч
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.config_manager import ConfigManager
    from src.calendar_alternatives import get_calendar_provider, CalendarEvent
    from src.drive_alternatives import get_drive_provider
    from src.notion_templates import create_page_with_template
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


class CalendarHandler:
    """Обработчик календаря для создания папок встреч."""
    
    def __init__(self, config_manager: ConfigManager, logger: Optional[logging.Logger] = None):
        """
        Инициализация обработчика календаря.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер (опционально)
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def process_account(self, account_type: str) -> Dict[str, Any]:
        """
        Обработка аккаунта (календарь и диск).
        
        Args:
            account_type: Тип аккаунта ('personal', 'work', 'both')
            
        Returns:
            Словарь с результатами обработки
        """
        self.logger.info(f"📅 Обработка аккаунта: {account_type}")
        
        try:
            if account_type == 'personal':
                if self.config_manager.is_personal_enabled():
                    self.logger.info("👤 Обрабатываю личный аккаунт")
                    # Получаем провайдер календаря
                    provider_config = self.config_manager.get_calendar_provider_config('personal')
                    calendar_provider = get_calendar_provider(**provider_config)
                    
                    if not calendar_provider:
                        self.logger.error("❌ Не удалось получить провайдер календаря")
                        return {"status": "error", "message": "Failed to get calendar provider"}
                    
                    # Получаем провайдер диска
                    drive_provider = get_drive_provider(
                        self.config_manager.get_drive_provider_type('personal'),
                        **self.config_manager.get_drive_provider_config('personal')
                    )
                    
                    if not drive_provider:
                        self.logger.warning("⚠️ Провайдер диска недоступен")
                    
                    # Обрабатываем календарные события
                    result = self.process_calendar_events(calendar_provider, drive_provider, account_type)
                    return result
                else:
                    self.logger.warning("⚠️ Личный аккаунт отключен")
                    return {"status": "skipped", "message": "Personal account disabled"}
            
            elif account_type == 'work':
                if self.config_manager.is_work_enabled():
                    self.logger.info("🏢 Обрабатываю рабочий аккаунт")
                    # Получаем провайдер календаря
                    provider_config = self.config_manager.get_calendar_provider_config('work')
                    calendar_provider = get_calendar_provider(**provider_config)
                    
                    if not calendar_provider:
                        self.logger.error("❌ Не удалось получить провайдер календаря")
                        return {"status": "error", "message": "Failed to get calendar provider"}
                    
                    # Получаем провайдер диска
                    drive_provider = get_drive_provider(
                        self.config_manager.get_drive_provider_type('work'),
                        **self.config_manager.get_drive_provider_config('work')
                    )
                    
                    if not drive_provider:
                        self.logger.warning("⚠️ Провайдер диска недоступен")
                    
                    # Обрабатываем календарные события
                    result = self.process_calendar_events(calendar_provider, drive_provider, account_type)
                    return result
                else:
                    self.logger.warning("⚠️ Рабочий аккаунт отключен")
                    return {"status": "skipped", "message": "Work account disabled"}
            
            elif account_type == 'both':
                results = []
                if self.config_manager.is_personal_enabled():
                    personal_result = self.process_account('personal')
                    results.append(personal_result)
                
                if self.config_manager.is_work_enabled():
                    work_result = self.process_account('work')
                    results.append(work_result)
                
                return {"status": "success", "message": "Both accounts processed", "results": results}
            
            else:
                self.logger.error(f"❌ Неизвестный тип аккаунта: {account_type}")
                return {"status": "error", "message": f"Unknown account type: {account_type}"}
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки аккаунта {account_type}: {e}")
            return {"status": "error", "message": str(e)}
    
    def process_calendar_events(self, calendar_provider, drive_provider, account_type: str) -> Dict[str, Any]:
        """
        Обработка календарных событий и создание папок встреч.
        
        Args:
            calendar_provider: Провайдер календаря
            drive_provider: Провайдер диска
            account_type: Тип аккаунта
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            self.logger.info(f"📅 Начинаю обработку календаря для {account_type} аккаунта...")
            
            # Получаем события на 2 дня вперед
            days = 2
            today = datetime.now().date()
            start_date = datetime.combine(today, datetime.min.time())
            end_date = start_date + timedelta(days=days)
            
            events = calendar_provider.get_events(start_date, end_date)
            self.logger.info(f"📅 Найдено событий: {len(events)}")
            
            # Фильтруем события
            filtered_events, excluded_events = self.filter_events(events, account_type)
            self.logger.info(f"✅ Отфильтровано событий: {len(filtered_events)}")
            self.logger.info(f"⏭️ Исключено событий: {len(excluded_events)}")
            
            # Обрабатываем события
            processed_events = 0
            processed_details = []
            
            for event in filtered_events:
                try:
                    result = self.process_event(event, drive_provider, account_type)
                    processed_details.append(result)
                    processed_events += 1
                    
                    # Выводим информацию о событии
                    self.logger.info(f"✅ Обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
            
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
            
            self.logger.info(f"📊 Статистика обработки: обработано {processed_events}, исключено {excluded_count}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
            return {'status': 'error', 'processed': 0, 'excluded': 0, 'errors': 1, 'details': [str(e)]}
    
    def filter_events(self, events: List[CalendarEvent], account_type: str) -> Tuple[List[CalendarEvent], List[Dict[str, Any]]]:
        """
        Фильтрация событий календаря.
        
        Args:
            events: Список событий
            account_type: Тип аккаунта
            
        Returns:
            Кортеж из списка отфильтрованных событий и списка исключенных событий
        """
        filtered_events = []
        excluded_events = []
        
        # Загружаем список исключений
        exclusions = self._load_exclusions(account_type)
        
        for event in events:
            # Исключаем события по ключевым словам
            is_excluded = False
            matched_keywords = []
            
            for keyword in exclusions:
                if keyword.lower() in event.title.lower():
                    is_excluded = True
                    matched_keywords.append(keyword)
            
            if is_excluded:
                self.logger.info(f"⏭️ Исключено событие: {event.title}")
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
            self.logger.info(f"✅ Добавлено событие: {event.title}")
        
        return filtered_events, excluded_events
    
    def _load_exclusions(self, account_type: str) -> List[str]:
        """
        Загрузка списка исключений для фильтрации событий.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Список ключевых слов для исключения
        """
        try:
            # Определяем путь к файлу исключений в зависимости от типа аккаунта
            exclusions_file = Path(f"config/{account_type}_exclusions.txt")
            
            if not exclusions_file.exists():
                self.logger.warning(f"⚠️ Файл исключений не найден: {exclusions_file}")
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
            
            self.logger.info(f"📋 Загружено {len(exclusions)} исключений из {exclusions_file}")
            return exclusions
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки исключений: {e}")
            # Возвращаем базовый список по умолчанию
            if account_type == 'personal':
                return ['День рождения', 'Дела', 'Личное', 'Personal', 'Отпуск']
            else:
                return ['Обед', 'Перерыв', 'Отгул', 'Больничный', 'Отпуск']
    
    def process_event(self, event: CalendarEvent, drive_provider, account_type: str) -> Dict[str, Any]:
        """
        Обработка события календаря и создание папки встречи.
        
        Args:
            event: Событие календаря
            drive_provider: Провайдер диска
            account_type: Тип аккаунта
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            self.logger.info(f"🔄 Обрабатываю событие: {event.title}")
            
            # Форматируем название папки
            folder_name = self.format_folder_name(event, account_type)
            
            # Проверяем существование папки
            if drive_provider and drive_provider.file_exists(folder_name):
                self.logger.info(f"📁 Папка уже существует: {folder_name}")
                folder_created = False
            else:
                # Создаем папку
                if drive_provider:
                    folder_id = drive_provider.create_folder(folder_name)
                    if folder_id:
                        self.logger.info(f"✅ Создана папка: {folder_name}")
                        folder_created = True
                    else:
                        self.logger.error(f"❌ Не удалось создать папку: {folder_name}")
                        folder_created = False
                else:
                    self.logger.warning("⚠️ Провайдер диска недоступен")
                    folder_created = False
            
            # Создаем страницу в Notion
            folder_link = f"file://{folder_name}" if folder_created else ""
            notion_page_id = self.create_notion_meeting_record(event, folder_link, account_type)
            
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
            
            self.logger.info(f"✅ Событие обработано: {event.title}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
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
    
    def format_folder_name(self, event: CalendarEvent, account_type: str) -> str:
        """
        Форматирование названия папки для встречи.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            Отформатированное название папки
        """
        start_time = event.start
        title = event.title
        
        # Формат: YYYY-MM-DD hh-mm Название встречи
        folder_name = f"{start_time.strftime('%Y-%m-%d %H-%M')} {title}"
        
        # Очищаем название от недопустимых символов
        folder_name = folder_name.replace('/', '-').replace('\\', '-').replace(':', '-')
        folder_name = folder_name.replace('*', '').replace('?', '').replace('"', '').replace('<', '').replace('>', '').replace('|', '')
        
        return folder_name
    
    def create_notion_meeting_record(self, event: CalendarEvent, folder_link: str, account_type: str) -> str:
        """
        Создание записи в Notion для встречи.
        
        Args:
            event: Событие календаря
            folder_link: Ссылка на папку встречи
            account_type: Тип аккаунта
            
        Returns:
            ID созданной страницы в Notion
        """
        try:
            # Загружаем шаблон
            template_path = "templates/meeting_page_template.json"
            if not os.path.exists(template_path):
                self.logger.error(f"❌ Шаблон не найден: {template_path}")
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
            notion_config = self.config_manager.get_notion_config()
            notion_token = notion_config.get('token')
            database_id = notion_config.get('database_id')
            
            if not notion_token or not database_id:
                self.logger.error("❌ Не настроены Notion токен или ID базы данных")
                return ""
            
            page_id = create_page_with_template(
                notion_token, 
                database_id, 
                template, 
                template_data
            )
            
            if page_id:
                self.logger.info(f"✅ Создана страница в Notion: {page_id}")
                return page_id
            else:
                self.logger.error("❌ Не удалось создать страницу в Notion")
                return ""
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания страницы в Notion: {e}")
            return ""


def get_calendar_handler(config_manager: ConfigManager, logger: Optional[logging.Logger] = None) -> CalendarHandler:
    """
    Получение обработчика календаря.
    
    Args:
        config_manager: Менеджер конфигурации
        logger: Логгер (опционально)
        
    Returns:
        Обработчик календаря
    """
    return CalendarHandler(config_manager, logger)
