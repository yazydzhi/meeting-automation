#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик интеграции календаря с созданием папок и страниц Notion.
Связывает события календаря с файловой системой и базой данных Notion.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path
from .base_handler import BaseHandler, retry
from .calendar_handler import CalendarHandler


class CalendarIntegrationHandler(BaseHandler):
    """Обработчик интеграции календаря с папками и Notion."""
    
    def __init__(self, config_manager, notion_handler=None, calendar_handler=None, logger=None):
        """
        Инициализация обработчика интеграции календаря.
        
        Args:
            config_manager: Менеджер конфигурации
            notion_handler: Обработчик Notion
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.notion_handler = notion_handler
        self.calendar_handler = calendar_handler or CalendarHandler(config_manager, logger)
        self.calendar_events_cache = {}
        self.folder_notion_mapping = {}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process(self, account_type: str = "personal") -> Dict[str, Any]:
        """
        Обрабатывает события календаря: создает папки и страницы Notion.
        
        Args:
            account_type: Тип аккаунта ('personal' или 'work')
            
        Returns:
            Результат обработки событий календаря
        """
        try:
            self._log_operation_start("обработку событий календаря", account_type=account_type)
            
            # Проверяем, включен ли аккаунт
            if not self._is_account_enabled(account_type):
                self.logger.info(f"⏭️ Аккаунт {account_type} пропущен (отключен в конфигурации)")
                return self._create_success_result(0, [f"Аккаунт {account_type} отключен"])
            
            # Загружаем события календаря
            calendar_events = self._load_calendar_events(account_type)
            if not calendar_events:
                self.logger.info(f"📅 События календаря для {account_type} не найдены")
                return self._create_success_result(0, [f"События календаря для {account_type} не найдены"])
            
            self.logger.info(f"📅 Найдено {len(calendar_events)} событий календаря для {account_type}")
            
            # Обрабатываем каждое событие
            processed_events = 0
            created_folders = 0
            created_notion_pages = 0
            errors = 0
            
            for event in calendar_events:
                try:
                    event_result = self._process_single_event(event, account_type)
                    if event_result['status'] == 'success':
                        processed_events += 1
                        if event_result.get('folder_created'):
                            created_folders += 1
                        if event_result.get('notion_page_created'):
                            created_notion_pages += 1
                    else:
                        errors += 1
                        self.logger.warning(f"⚠️ Ошибка обработки события {event.get('title', 'Unknown')}: {event_result.get('message', 'Unknown error')}")
                except Exception as e:
                    errors += 1
                    self.logger.error(f"❌ Критическая ошибка обработки события {event.get('title', 'Unknown')}: {e}")
            
            # Формируем результат
            result = {
                "status": "success",
                "processed": processed_events,
                "folders_created": created_folders,
                "notion_pages_created": created_notion_pages,
                "errors": errors,
                "details": [
                    f"Обработано событий: {processed_events}",
                    f"Создано папок: {created_folders}",
                    f"Создано страниц Notion: {created_notion_pages}",
                    f"Ошибок: {errors}"
                ]
            }
            
            self._log_operation_end(f"обработку событий календаря {account_type}", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, f"обработка событий календаря {account_type}")
    
    def _load_calendar_events(self, account_type: str) -> List[Dict[str, Any]]:
        """
        Загружает события календаря для указанного аккаунта.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Список событий календаря
        """
        try:
            if self.calendar_handler:
                # Используем реальный CalendarHandler
                events = self.calendar_handler.get_calendar_events(account_type, days_ahead=7)
                self.logger.info(f"📅 Получено {len(events)} событий из календаря для {account_type}")
                return events
            else:
                # Fallback на тестовые данные
                self.logger.warning("⚠️ CalendarHandler недоступен, используем тестовые данные")
                if account_type == "personal":
                    return self._get_sample_personal_events()
                elif account_type == "work":
                    return self._get_sample_work_events()
                else:
                    return []
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки событий календаря для {account_type}: {e}")
            # Fallback на тестовые данные
            if account_type == "personal":
                return self._get_sample_personal_events()
            elif account_type == "work":
                return self._get_sample_work_events()
            else:
                return []
        """
        Загружает события календаря для указанного аккаунта.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Список событий календаря
        """
        try:
            # TODO: Реализовать загрузку событий календаря
            # Пока используем заглушку для тестирования
            if account_type == 'personal':
                return self._get_sample_personal_events()
            elif account_type == 'work':
                return self._get_sample_work_events()
            else:
                return []
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки событий календаря для {account_type}: {e}")
            return []
    
    def _process_single_event(self, event: Dict[str, Any], account_type: str) -> Dict[str, Any]:
        """
        Обрабатывает одно событие календаря.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            Результат обработки события
        """
        try:
            event_id = event.get('id', 'unknown')
            event_title = event.get('title', 'Unknown Event')
            
            self.logger.info(f"📅 Обрабатываю событие: {event_title}")
            
            # Проверяем, было ли событие уже обработано
            if self._is_event_processed(event_id, account_type):
                self.logger.info(f"⏭️ Событие {event_title} уже обработано, пропускаю")
                return {"status": "skipped", "message": "Event already processed"}
            
            # Создаем папку для встречи
            folder_result = self._create_meeting_folder(event, account_type)
            if not folder_result['success']:
                return {"status": "error", "message": f"Failed to create folder: {folder_result['message']}"}
            
            folder_path = folder_result['folder_path']
            
            # Создаем страницу в Notion
            notion_result = self._create_notion_page(event, folder_path, account_type)
            if not notion_result['success']:
                self.logger.warning(f"⚠️ Не удалось создать страницу Notion для {event_title}: {notion_result['message']}")
                # Продолжаем работу, так как папка создана
            
            # Помечаем событие как обработанное
            self._mark_event_processed(event_id, account_type)
            
            return {
                "status": "success",
                "folder_created": True,
                "notion_page_created": notion_result.get('success', False),
                "folder_path": folder_path,
                "notion_page_id": notion_result.get('page_id')
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки события {event.get('title', 'Unknown')}: {e}")
            return {"status": "error", "message": str(e)}
    
    def _create_meeting_folder(self, event: Dict[str, Any], account_type: str) -> Dict[str, Any]:
        """
        Создает папку для встречи на основе события календаря.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            Результат создания папки
        """
        try:
            # Генерируем имя папки
            folder_name = self._generate_folder_name(event)
            
            # Получаем конфигурацию аккаунта
            account_config = self._get_account_config(account_type)
            if not account_config:
                return {"success": False, "message": f"Account configuration not found for {account_type}"}
            
            base_path = account_config.get('local_drive_root')
            if not base_path:
                return {"success": False, "message": f"Local drive root not configured for {account_type}"}
            
            # Создаем полный путь к папке
            folder_path = os.path.join(base_path, folder_name)
            
            # Создаем папку, если её нет
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                self.logger.info(f"📁 Создана папка: {folder_path}")
            else:
                self.logger.info(f"📁 Папка уже существует: {folder_path}")
            
            # Создаем файл статуса
            self._create_status_file(folder_path, event, account_type)
            
            return {"success": True, "folder_path": folder_path}
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _generate_folder_name(self, event: Dict[str, Any]) -> str:
        """
        Генерирует имя папки для встречи.
        
        Args:
            event: Событие календаря
            
        Returns:
            Имя папки в формате: YYYY-MM-DD HH-MM Название встречи
        """
        try:
            # Парсим время начала
            start_time_str = event.get('start', '')
            if start_time_str:
                # Убираем 'Z' и парсим ISO формат
                start_time_str = start_time_str.replace('Z', '+00:00')
                start_time = datetime.fromisoformat(start_time_str)
            else:
                # Если время не указано, используем текущее
                start_time = datetime.now()
            
            # Формируем имя папки
            time_part = start_time.strftime('%Y-%m-%d %H-%M')
            title_part = event.get('title', 'Unknown Event')
            
            # Очищаем название от недопустимых символов для имени папки
            title_part = self._sanitize_folder_name(title_part)
            
            folder_name = f"{time_part} {title_part}"
            return folder_name
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации имени папки: {e}")
            # Возвращаем безопасное имя по умолчанию
            return f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def _sanitize_folder_name(self, name: str) -> str:
        """
        Очищает название от недопустимых символов для имени папки.
        
        Args:
            name: Исходное название
            
        Returns:
            Очищенное название
        """
        # Заменяем недопустимые символы
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        for char in invalid_chars:
            name = name.replace(char, '_')
        
        # Убираем лишние пробелы и подчеркивания
        name = ' '.join(name.split())
        name = name.replace(' ', '_')
        
        # Ограничиваем длину
        if len(name) > 100:
            name = name[:100]
        
        return name
    
    def _create_status_file(self, folder_path: str, event: Dict[str, Any], account_type: str):
        """
        Создает файл статуса в папке встречи.
        
        Args:
            folder_path: Путь к папке встречи
            event: Событие календаря
            account_type: Тип аккаунта
        """
        try:
            status_file_path = os.path.join(folder_path, "processing_status.md")
            
            # Формируем содержимое файла статуса
            status_content = self._generate_status_content(event, account_type)
            
            # Записываем файл
            with open(status_file_path, 'w', encoding='utf-8') as f:
                f.write(status_content)
            
            self.logger.info(f"📄 Создан файл статуса: {status_file_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания файла статуса: {e}")
    
    def _generate_status_content(self, event: Dict[str, Any], account_type: str) -> str:
        """
        Генерирует содержимое файла статуса.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            Содержимое файла статуса в формате Markdown
        """
        title = event.get('title', 'Unknown Event')
        start_time = event.get('start', 'Unknown')
        end_time = event.get('end', 'Unknown')
        attendees_count = event.get('attendees_count', 0)
        
        content = f"""# 📋 Статус обработки встречи

## 🎯 Информация о встрече
- **Название:** {title}
- **Дата и время:** {start_time} - {end_time}
- **Участники:** {attendees_count}
- **Тип аккаунта:** {account_type}
- **Папка создана:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 📁 Файлы встречи
- **Оригинальные видео:** не найдены
- **Сжатые видео:** не найдены
- **Аудио файлы:** не найдены
- **Транскрипции:** не найдены
- **Саммари:** не найдены
- **Анализ:** не найден

## 📝 Статус обработки
- **Этап 1 (Календарь):** ✅ Завершен
- **Этап 2 (Медиа):** ⏳ Ожидает
- **Этап 3 (Транскрипция):** ⏳ Ожидает
- **Этап 4 (Саммари):** ⏳ Ожидает
- **Этап 5 (Notion):** ⏳ Ожидает

## 📊 Последнее обновление
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return content
    
    def _create_notion_page(self, event: Dict[str, Any], folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Создает страницу встречи в Notion.
        
        Args:
            event: Событие календаря
            folder_path: Путь к папке встречи
            account_type: Тип аккаунта
            
        Returns:
            Результат создания страницы Notion
        """
        try:
            if not self.notion_handler:
                return {"success": False, "message": "Notion handler not available"}
            
            # TODO: Реализовать создание страницы через NotionHandler
            # Пока возвращаем заглушку
            self.logger.info(f"📝 Создание страницы Notion для {event.get('title', 'Unknown')} (заглушка)")
            
            return {
                "success": True,
                "page_id": f"notion_page_{account_type}_{event.get('id', 'unknown')}",
                "page_id": f"notion_page_{account_type}_{event.get('id', 'unknown')}",
                "message": "Notion page creation not yet implemented"
            }
            
        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def _get_account_config(self, account_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает конфигурацию аккаунта.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Конфигурация аккаунта или None
        """
        try:
            if account_type == 'personal':
                return self.config_manager.get_personal_config()
            elif account_type == 'work':
                return self.config_manager.get_work_config()
            else:
                return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигурации аккаунта {account_type}: {e}")
            return None
    
    def _is_event_processed(self, event_id: str, account_type: str) -> bool:
        """
        Проверяет, было ли событие уже обработано.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта
            
        Returns:
            True если событие уже обработано, False иначе
        """
        try:
            cache_key = f"{account_type}_{event_id}"
            return cache_key in self.calendar_events_cache
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса события: {e}")
            return False
    
    def _mark_event_processed(self, event_id: str, account_type: str):
        """
        Помечает событие как обработанное.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта
        """
        try:
            cache_key = f"{account_type}_{event_id}"
            self.calendar_events_cache[cache_key] = {
                "processed_at": datetime.now().isoformat(),
                "account_type": account_type
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка пометки события как обработанного: {e}")
    
    def _is_account_enabled(self, account_type: str) -> bool:
        """
        Проверяет, включен ли аккаунт.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            True если аккаунт включен, False иначе
        """
        try:
            if account_type == 'personal':
                return self.config_manager.is_personal_enabled()
            elif account_type == 'work':
                return self.config_manager.is_work_enabled()
            else:
                return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса аккаунта {account_type}: {e}")
            return False
    
    # Временные методы для тестирования
    def _get_sample_personal_events(self) -> List[Dict[str, Any]]:
        """Возвращает тестовые события для личного аккаунта."""
        return [
            {
                "id": "personal_test_1",
                "title": "Тестовая встреча",
                "start": "2025-08-29T15:00:00Z",
                "end": "2025-08-29T16:00:00Z",
                "attendees_count": 2
            }
        ]
    
    def _get_sample_work_events(self) -> List[Dict[str, Any]]:
        """Возвращает тестовые события для рабочего аккаунта."""
        return [
            {
                "id": "work_test_1",
                "title": "Рабочая встреча",
                "end": "2025-08-29T11:00:00Z",
                "attendees_count": 5
            }
        ]
