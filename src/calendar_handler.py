#!/usr/bin/env python3
"""
Модуль для работы с календарем и создания папок встреч
"""

import os
import sys
import logging
import json
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
    """Обработчик календарных событий."""
    
    def __init__(self, config_manager: ConfigManager):
        """
        Инициализация обработчика календаря.
        
        Args:
            config_manager: Менеджер конфигурации
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        
        # Кэш для отслеживания обработанных событий
        self.processed_events_cache = self._load_processed_events_cache()
        
        # Время последней синхронизации для каждого аккаунта
        self.last_sync_time = self._load_last_sync_time()
    
    def _load_processed_events_cache(self) -> Dict[str, Any]:
        """Загрузка кэша обработанных событий."""
        try:
            cache_file = Path('data/processed_events_cache.json')
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                self.logger.info(f"✅ Кэш обработанных событий загружен: {len(cache.get('events', {}))} событий")
                return cache
            else:
                self.logger.info("⚠️ Кэш обработанных событий не найден, создаю новый")
                return {"events": {}, "last_updated": datetime.now().isoformat()}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки кэша событий: {e}")
            return {"events": {}, "last_updated": datetime.now().isoformat()}
    
    def _save_processed_events_cache(self):
        """Сохранение кэша обработанных событий."""
        try:
            cache_dir = Path('data')
            cache_dir.mkdir(exist_ok=True)
            
            cache_file = cache_dir / 'processed_events_cache.json'
            
            # Обновляем время последнего обновления
            self.processed_events_cache["last_updated"] = datetime.now().isoformat()
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_events_cache, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"✅ Кэш обработанных событий сохранен в {cache_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения кэша событий: {e}")
    
    def _load_last_sync_time(self) -> Dict[str, str]:
        """Загрузка времени последней синхронизации."""
        try:
            sync_file = Path('data/last_sync_time.json')
            if sync_file.exists():
                with open(sync_file, 'r', encoding='utf-8') as f:
                    sync_times = json.load(f)
                self.logger.info(f"✅ Время последней синхронизации загружено")
                return sync_times
            else:
                self.logger.info("⚠️ Файл времени синхронизации не найден, создаю новый")
                return {"personal": "", "work": ""}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки времени синхронизации: {e}")
            return {"personal": "", "work": ""}
    
    def _save_last_sync_time(self):
        """Сохранение времени последней синхронизации."""
        try:
            sync_dir = Path('data')
            sync_dir.mkdir(exist_ok=True)
            
            sync_file = sync_dir / 'last_sync_time.json'
            
            with open(sync_file, 'w', encoding='utf-8') as f:
                json.dump(self.last_sync_time, f, ensure_ascii=False, indent=2)
            
            self.logger.debug(f"✅ Время синхронизации сохранено в {sync_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения времени синхронизации: {e}")
    
    def _is_event_processed(self, event: CalendarEvent, account_type: str) -> bool:
        """
        Проверка, было ли событие уже обработано.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            True если событие уже обработано
        """
        # Создаем уникальный ключ для события
        event_key = f"{account_type}_{event.event_id}_{event.start.isoformat()}"
        
        # Проверяем в кэше
        if event_key in self.processed_events_cache.get("events", {}):
            cached_event = self.processed_events_cache["events"][event_key]
            
            # Проверяем, не изменилось ли событие
            if (cached_event.get("title") == event.title and 
                cached_event.get("end") == event.end.isoformat() and
                cached_event.get("attendees_count") == len(event.attendees)):
                return True
        
        return False
    
    def _mark_event_processed(self, event: CalendarEvent, account_type: str, result: Dict[str, Any]):
        """
        Отмечает событие как обработанное в кэше.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            result: Результат обработки
        """
        event_key = f"{account_type}_{event.event_id}_{event.start.isoformat()}"
        
        # Сохраняем информацию о событии (конвертируем datetime в строки)
        self.processed_events_cache["events"][event_key] = {
            "title": event.title,
            "start": event.start.isoformat(),
            "end": event.end.isoformat(),
            "attendees_count": len(event.attendees),
            "processed_at": datetime.now().isoformat(),
            "result": {
                "title": result.get("title", ""),
                "start": result.get("start").isoformat() if hasattr(result.get("start"), 'isoformat') else str(result.get("start", "")),
                "end": result.get("end").isoformat() if hasattr(result.get("end"), 'isoformat') else str(result.get("end", "")),
                "attendees_count": result.get("attendees_count", 0)
            }
        }
        
        # Сохраняем кэш
        self._save_processed_events_cache()
    
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
                    drive_config = self.config_manager.get_drive_provider_config('personal')
                    drive_provider = get_drive_provider(**drive_config)
                    
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
                    drive_config = self.config_manager.get_drive_provider_config('work')
                    drive_provider = get_drive_provider(**drive_config)
                    
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
            
            # Получаем события на 2 дня назад + 2 дня вперед (всего 5 дней)
            days_back = 2
            days_forward = 2
            today = datetime.now().date()
            start_date = datetime.combine(today - timedelta(days=days_back), datetime.min.time())
            end_date = datetime.combine(today + timedelta(days=days_forward), datetime.max.time())
            
            events = calendar_provider.get_events(start_date, end_date)
            self.logger.info(f"📅 Найдено событий за период {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}: {len(events)}")
            
            # Фильтруем события
            filtered_events, excluded_events = self.filter_events(events, account_type)
            self.logger.info(f"✅ Отфильтровано событий: {len(filtered_events)}")
            self.logger.info(f"⏭️ Исключено событий: {len(excluded_events)}")
            
            # Проверяем, какие события уже обработаны
            new_events = []
            already_processed = 0
            
            for event in filtered_events:
                if self._is_event_processed(event, account_type):
                    already_processed += 1
                    self.logger.debug(f"⏭️ Событие уже обработано: {event.title}")
                else:
                    new_events.append(event)
            
            self.logger.info(f"🆕 Новых событий для обработки: {len(new_events)}")
            self.logger.info(f"✅ Уже обработано событий: {already_processed}")
            
            # Обрабатываем только новые события
            processed_events = 0
            processed_details = []
            
            for event in new_events:
                try:
                    result = self.process_event(event, drive_provider, account_type)
                    processed_details.append(result)
                    processed_events += 1
                    
                    # Отмечаем событие как обработанное
                    self._mark_event_processed(event, account_type, result)
                    
                    # Выводим информацию о событии
                    self.logger.info(f"✅ Обработано: {event.title} | {event.start.strftime('%H:%M')} | Участники: {len(event.attendees)}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки события {event.title}: {e}")
            
            # Обновляем время последней синхронизации
            self.last_sync_time[account_type] = datetime.now().isoformat()
            self._save_last_sync_time()
            
            # Статистика
            excluded_count = len(excluded_events)
            total_events = len(filtered_events)
            
            result = {
                'status': 'success',
                'processed': processed_events,
                'total': total_events,
                'new': len(new_events),
                'already_processed': already_processed,
                'excluded': excluded_count,
                'errors': len(new_events) - processed_events,
                'details': processed_details,
                'excluded_details': excluded_events,
                'message': f"Обработано {processed_events} новых событий из {total_events} всего"
            }
            
            if processed_events == 0:
                result['message'] = f"Новых событий нет, уже обработано {already_processed} из {total_events}"
            
            self.logger.info(f"📊 Статистика обработки: новых {processed_events}, уже обработано {already_processed}, исключено {excluded_count}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
            return {'status': 'error', 'processed': 0, 'total': 0, 'new': 0, 'already_processed': 0, 'excluded': 0, 'errors': 1, 'details': [str(e)], 'message': str(e)}
    
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
            folder_created = False
            folder_id = None
            
            if drive_provider and drive_provider.file_exists(folder_name):
                self.logger.info(f"📁 Папка уже существует: {folder_name}")
                folder_created = False
            else:
                # Создаем папку только если её нет
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
            
            # Создаем страницу в Notion только если папка была создана или если её нет
            notion_page_id = ""
            if folder_created or not drive_provider.file_exists(folder_name):
                # Передаем полный путь к папке для сохранения в Notion
                full_folder_path = os.path.join(drive_provider.get_root_path() if drive_provider else "", folder_name)
                notion_page_id = self.create_notion_meeting_record(event, full_folder_path, account_type)
                
                if notion_page_id:
                    self.logger.info(f"✅ Страница Notion создана/обновлена: {notion_page_id}")
                else:
                    self.logger.warning(f"⚠️ Не удалось создать страницу Notion для: {event.title}")
            else:
                self.logger.info(f"⏭️ Папка и страница Notion уже существуют для: {event.title}")
            
            # Формируем результат
            result = {
                'title': event.title,
                'start': event.start,
                'end': event.end,
                'attendees_count': len(event.attendees),
                'has_meeting_link': bool(event.meeting_link),
                'drive_folder_created': folder_created,
                'notion_page_id': notion_page_id,
                'drive_folder_link': os.path.join(drive_provider.get_root_path() if drive_provider else "", folder_name) if folder_name else ""
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
            self.logger.info(f"🔧 Начинаю создание страницы в Notion для события: {event.title}")
            
            # Загружаем шаблон
            template_path = "templates/meeting_page_template.json"
            if not os.path.exists(template_path):
                self.logger.error(f"❌ Шаблон не найден: {template_path}")
                return ""
            
            self.logger.info(f"✅ Шаблон загружен: {template_path}")
            
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
                "account_type": account_type,
                "event_id": event.event_id
            }
            
            self.logger.info(f"📋 Данные события подготовлены: {template_data}")
            
            # Получаем настройки Notion
            self.logger.info(f"🔧 Получаю настройки Notion...")
            notion_config = self.config_manager.get_notion_config()
            notion_token = notion_config.get('token')
            database_id = notion_config.get('database_id')
            
            self.logger.info(f"📋 Настройки Notion: токен={'*' * 10 + notion_token[-4:] if notion_token else 'НЕТ'}, база={database_id}")
            
            if not notion_token or not database_id:
                self.logger.error("❌ Не настроены Notion токен или ID базы данных")
                return ""
            
            # Проверяем существование страницы перед созданием
            from .notion_templates import check_page_exists
            existing_page_id = check_page_exists(
                notion_token, 
                database_id, 
                event.title, 
                event.start.strftime('%Y-%m-%d'),
                self.logger
            )
            
            if existing_page_id:
                self.logger.info(f"⏭️ Страница в Notion уже существует: {existing_page_id}")
                return existing_page_id
            
            self.logger.info(f"🔧 Вызываю create_page_with_template...")
            page_id = create_page_with_template(
                notion_token, 
                database_id, 
                template_data, 
                template,
                self.logger
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
    return CalendarHandler(config_manager)
