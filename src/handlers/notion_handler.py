#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для синхронизации с Notion
"""

from typing import Dict, Any, List
from .base_handler import BaseHandler, retry
import os
import pytz
from datetime import datetime


class NotionHandler(BaseHandler):
    """Обработчик синхронизации с Notion."""
    
    def __init__(self, config_manager, notion_handler=None, logger=None):
        """
        Инициализация обработчика Notion.
        
        Args:
            config_manager: Менеджер конфигурации
            notion_handler: Существующий обработчик Notion (если есть)
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.notion_handler = notion_handler
        self.last_notion_stats = {}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Основной метод синхронизации с Notion.
        
        Returns:
            Результат синхронизации
        """
        try:
            self._log_operation_start("синхронизацию с Notion")
            
            # Пытаемся использовать существующий обработчик
            if self.notion_handler:
                result = self.notion_handler.sync_with_notion()
                self.last_notion_stats = result
                self._log_operation_end("синхронизацию с Notion", result)
                return result
            
            # Используем собственную логику
            result = self._sync_with_notion()
            self.last_notion_stats = result
            self._log_operation_end("синхронизацию с Notion", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, "синхронизация с Notion")
    
    def _sync_with_notion(self) -> Dict[str, Any]:
        """
        Синхронизация с Notion.
        
        Returns:
            Результат синхронизации
        """
        try:
            self.logger.info("📝 Запуск синхронизации с Notion...")
            
            # Проверяем конфигурацию Notion
            if not self._validate_notion_config():
                return self._create_error_result(
                    Exception("Не настроена конфигурация Notion"), 
                    "валидация конфигурации"
                )
            
            # Здесь будет логика синхронизации с Notion
            # TODO: Реализовать через NotionHandler
            
            notion_stats = {
                "status": "success", 
                "synced": 0, 
                "errors": 0, 
                "details": ["Синхронизация с Notion пока не реализована"]
            }
            
            # Сохраняем статистику для детальных отчетов
            self.last_notion_stats = notion_stats
            
            return notion_stats
            
        except Exception as e:
            return self._create_error_result(e, "синхронизация с Notion")
    
    def _validate_notion_config(self) -> bool:
        """
        Проверяет корректность конфигурации Notion.
        
        Returns:
            True если конфигурация корректна, False иначе
        """
        try:
            notion_config = self.config_manager.get_notion_config()
            token = notion_config.get('token')
            database_id = notion_config.get('database_id')
            
            if not token:
                self.logger.error("❌ Не настроен Notion токен")
                return False
            
            if not database_id:
                self.logger.error("❌ Не настроен ID базы данных Notion")
                return False
            
            self.logger.info("✅ Конфигурация Notion корректна")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации конфигурации Notion: {e}")
            return False
    
    def get_notion_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию Notion.
        
        Returns:
            Конфигурация Notion или пустой словарь
        """
        try:
            if hasattr(self.config_manager, 'get_notion_config'):
                return self.config_manager.get_notion_config()
            else:
                self.logger.warning("⚠️ ConfigManager не поддерживает get_notion_config")
                return {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигурации Notion: {e}")
            return {}
    
    def create_meeting_page(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        TASK-4: Создает страницу встречи в Notion с исправленной логикой таймзон.
        
        Args:
            event_data: Данные события с учетом таймзон
            
        Returns:
            Результат создания страницы
        """
        try:
            self.logger.info(f"🔧 TASK-4: Создание страницы встречи с исправленной логикой таймзон")
            self.logger.info(f"📝 Название: {event_data.get('title', 'Без названия')}")
            
            # Проверяем конфигурацию
            if not self._validate_notion_config():
                return self._create_error_result(
                    Exception("Не настроена конфигурация Notion"), 
                    "создание страницы встречи"
                )
            
            # TASK-4: Получаем настройки таймзоны
            timezone_str = self.config_manager.get_general_config().get('timezone', 'Europe/Moscow')
            timezone = pytz.timezone(timezone_str)
            
            self.logger.info(f"🔧 Используется таймзона: {timezone_str}")
            
            # TASK-4: Обрабатываем время с учетом таймзон
            start_dt = event_data.get('start')
            end_dt = event_data.get('end')
            
            if start_dt and end_dt:
                try:
                    # Убеждаемся, что datetime объекты имеют таймзону
                    if not start_dt.tzinfo:
                        start_dt = timezone.localize(start_dt)
                    if not end_dt.tzinfo:
                        end_dt = timezone.localize(end_dt)
                    
                    # Конвертируем в нашу таймзону
                    start_dt = start_dt.astimezone(timezone)
                    end_dt = end_dt.astimezone(timezone)
                    
                    self.logger.info(f"🔧 Время начала в {timezone}: {start_dt.strftime('%Y-%m-%d %H:%M %Z')}")
                    self.logger.info(f"🔧 Время окончания в {timezone}: {end_dt.strftime('%Y-%m-%d %H:%M %Z')}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка обработки времени: {e}")
            
            # TASK-4: Создаем свойства страницы с учетом таймзон
            properties = self._create_meeting_properties(event_data, timezone)
            
            # TODO: Реализовать реальный API запрос к Notion
            # Пока что возвращаем заглушку с исправленной логикой таймзон
            
            result = {
                "status": "success",
                "page_id": "test_page_id_tz_fixed",
                "message": "Страница встречи создана с исправленной логикой таймзон (заглушка)"
            }
            
            self.logger.info(f"✅ Страница встречи создана: {result['page_id']}")
            return result
            
        except Exception as e:
            return self._create_error_result(e, "создание страницы встречи")
    
    def update_meeting_page(self, page_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обновляет страницу встречи в Notion.
        
        Args:
            page_id: ID страницы
            update_data: Данные для обновления
            
        Returns:
            Результат обновления
        """
        try:
            self.logger.info(f"📝 Обновление страницы встречи: {page_id}")
            
            # Проверяем конфигурацию
            if not self._validate_notion_config():
                return self._create_error_result(
                    Exception("Не настроена конфигурация Notion"), 
                    "обновление страницы встречи"
                )
            
            # Здесь будет логика обновления страницы
            # TODO: Интегрировать с существующей логикой обновления страниц
            
            result = {
                "status": "success",
                "page_id": page_id,
                "message": "Страница встречи обновлена (заглушка)"
            }
            
            self.logger.info(f"✅ Страница встречи обновлена: {page_id}")
            return result
            
        except Exception as e:
            return self._create_error_result(e, "обновление страницы встречи")
    
    def search_meeting_page(self, title: str, date: str) -> Dict[str, Any]:
        """
        Ищет страницу встречи в Notion.
        
        Args:
            title: Название встречи
            date: Дата встречи
            
        Returns:
            Результат поиска
        """
        try:
            self.logger.info(f"🔍 Поиск страницы встречи: {title} ({date})")
            
            # Проверяем конфигурацию
            if not self._validate_notion_config():
                return self._create_error_result(
                    Exception("Не настроена конфигурация Notion"), 
                    "поиск страницы встречи"
                )
            
            # Здесь будет логика поиска страницы
            # TODO: Интегрировать с существующей логикой поиска страниц
            
            result = {
                "status": "success",
                "found": False,
                "page_id": None,
                "message": "Поиск выполнен (заглушка)"
            }
            
            self.logger.info(f"✅ Поиск страницы встречи завершен: найдено {result['found']}")
            return result
            
        except Exception as e:
            return self._create_error_result(e, "поиск страницы встречи")
    
    def get_notion_stats(self) -> Dict[str, Any]:
        """
        Получает последнюю статистику синхронизации с Notion.
        
        Returns:
            Последняя статистика
        """
        return self.last_notion_stats
    
    def reset_notion_stats(self):
        """Сбрасывает статистику синхронизации с Notion."""
        self.last_notion_stats = {}
        self.logger.info("📊 Статистика Notion сброшена")
    
    def _create_meeting_properties(self, event_data: Dict[str, Any], timezone: pytz.timezone) -> Dict[str, Any]:
        """
        TASK-4: Создает свойства страницы встречи с учетом таймзон.
        
        Args:
            event_data: Данные события
            timezone: Объект таймзоны
            
        Returns:
            Словарь свойств страницы
        """
        try:
            properties = {}
            
            # Название встречи
            if event_data.get('title'):
                properties['Name'] = {
                    "title": [
                        {
                            "text": {
                                "content": str(event_data['title'])
                            }
                        }
                    ]
                }
            
            # TASK-4: Дата и время с учетом таймзоны
            start_dt = event_data.get('start')
            end_dt = event_data.get('end')
            
            if start_dt and end_dt:
                try:
                    # Убеждаемся, что datetime объекты имеют таймзону
                    if not start_dt.tzinfo:
                        start_dt = timezone.localize(start_dt)
                    if not end_dt.tzinfo:
                        end_dt = timezone.localize(end_dt)
                    
                    # Конвертируем в нашу таймзону
                    start_dt = start_dt.astimezone(timezone)
                    end_dt = end_dt.astimezone(timezone)
                    
                    properties['Date & Time'] = {
                        "date": {
                            "start": start_dt.isoformat(),
                            "end": end_dt.isoformat()
                        }
                    }
                    
                    self.logger.info(f"🔧 Время встречи обработано с таймзоной: {start_dt.strftime('%Y-%m-%d %H:%M')} - {end_dt.strftime('%H:%M')}")
                    
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка обработки времени встречи: {e}")
            
            # Описание
            if event_data.get('description'):
                properties['Description'] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": str(event_data['description'])
                            }
                        }
                    ]
                }
            
            # Место
            if event_data.get('location'):
                properties['Location'] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": str(event_data['location'])
                            }
                        }
                    ]
                }
            
            # Участники
            if event_data.get('attendees'):
                attendees = event_data.get('attendees')
                if isinstance(attendees, list):
                    attendee_text = ", ".join([str(attendee) for attendee in attendees])
                else:
                    attendee_text = str(attendees)
                
                properties['Attendees'] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": attendee_text
                            }
                        }
                    ]
                }
            
            # Ссылка на встречу
            if event_data.get('meeting_link'):
                properties['Meeting Link'] = {
                    "url": str(event_data['meeting_link'])
                }
            
            # Ссылка на папку
            if event_data.get('folder_link'):
                properties['Folder Link'] = {
                    "url": str(event_data['folder_link'])
                }
            
            # Источник календаря
            if event_data.get('calendar_source'):
                properties['Calendar Source'] = {
                    "select": {
                        "name": str(event_data['calendar_source'])
                    }
                }
            
            # Тип аккаунта
            if event_data.get('account_type'):
                properties['Account Type'] = {
                    "select": {
                        "name": str(event_data['account_type'])
                    }
                }
            
            # TASK-4: Метаданные о таймзоне
            properties['Timezone'] = {
                "rich_text": [
                    {
                        "text": {
                            "content": str(timezone)
                        }
                    }
                ]
            }
            
            properties['Created At'] = {
                "date": {
                    "start": timezone.localize(datetime.now()).isoformat()
                }
            }
            
            self.logger.info(f"✅ Создано {len(properties)} свойств для страницы встречи")
            return properties
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания свойств страницы встречи: {e}")
            return {}
