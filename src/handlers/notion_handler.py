#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для синхронизации с Notion
"""

from typing import Dict, Any, List, Optional
from .base_handler import BaseHandler, retry
from .notion_api import NotionAPI
import os
import pytz
from datetime import datetime
import sys
sys.path.append("src")
from notion_templates import create_customized_template


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
        self.notion_api = NotionAPI(config_manager, logger)
        self.last_notion_stats = {}
        
        # Инициализируем StateManager для отслеживания синхронизации с Notion
        try:
            from .state_manager import StateManager
            self.state_manager = StateManager(logger=self.logger)
            self.logger.info("✅ StateManager инициализирован в NotionHandler")
        except Exception as e:
            self.logger.warning(f"⚠️ StateManager недоступен в NotionHandler: {e}")
            self.state_manager = None
    
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
            
            # Реальная логика создания страницы в Notion
            try:
                # Импортируем notion_templates для создания страницы
                from notion_templates import create_meeting_page
                
                # Создаем реальную страницу в Notion
                notion_result = create_meeting_page(event_data, self.config_manager)
                
                if notion_result and notion_result.get('status') == 'success':
                    page_id = notion_result.get('page_id', 'unknown')
                    page_url = notion_result.get('page_url', '')
                    
                    # Помечаем событие как синхронизированное с Notion в БД
                    if self.state_manager and event_data.get('id'):
                        self.state_manager.mark_notion_synced(
                            event_data['id'], 
                            page_id, 
                            page_url, 
                            "success"
                        )
                    
                    result = {
                        "status": "success",
                        "page_id": page_id,
                        "page_url": page_url,
                        "message": "Страница встречи успешно создана в Notion"
                    }
                else:
                    result = {
                        "status": "error",
                        "page_id": None,
                        "message": f"Ошибка создания страницы в Notion: {notion_result.get('message', 'Unknown error')}"
                    }
                    
            except ImportError:
                self.logger.warning("⚠️ Модуль notion_templates не найден, используем заглушку")
                result = {
                    "status": "warning",
                    "page_id": "notion_templates_missing",
                    "message": "Модуль notion_templates не найден, страница не создана"
                }
            except Exception as e:
                self.logger.error(f"❌ Ошибка создания страницы в Notion: {e}")
                result = {
                    "status": "error",
                    "page_id": None,
                    "message": f"Ошибка создания страницы в Notion: {str(e)}"
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
            
            # Реальная логика обновления страницы в Notion
            try:
                # Импортируем notion_templates для обновления страницы
                from notion_templates import update_meeting_page
                
                # Обновляем реальную страницу в Notion
                notion_result = update_meeting_page(page_id, update_data, self.config_manager)
                
                if notion_result and notion_result.get('status') == 'success':
                    # Помечаем событие как синхронизированное с Notion в БД
                    if self.state_manager and update_data.get('event_id'):
                        self.state_manager.mark_notion_synced(
                            update_data['event_id'], 
                            page_id, 
                            notion_result.get('page_url', ''), 
                            "success"
                        )
                    
                    result = {
                        "status": "success",
                        "page_id": page_id,
                        "message": "Страница встречи успешно обновлена в Notion"
                    }
                else:
                    result = {
                        "status": "error",
                        "page_id": page_id,
                        "message": f"Ошибка обновления страницы в Notion: {notion_result.get('message', 'Unknown error')}"
                    }
                    
            except ImportError:
                self.logger.warning("⚠️ Модуль notion_templates не найден, используем заглушку")
                result = {
                    "status": "warning",
                    "page_id": page_id,
                    "message": "Модуль notion_templates не найден, страница не обновлена"
                }
            except Exception as e:
                self.logger.error(f"❌ Ошибка обновления страницы в Notion: {e}")
                result = {
                    "status": "error",
                    "page_id": page_id,
                    "message": f"Ошибка обновления страницы в Notion: {str(e)}"
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
            
            # Реальная логика поиска страницы в Notion
            try:
                # Импортируем notion_templates для поиска страницы
                from notion_templates import search_meeting_page
                
                # Ищем реальную страницу в Notion
                notion_result = search_meeting_page(title, date, self.config_manager)
                
                if notion_result and notion_result.get('status') == 'success':
                    result = {
                        "status": "success",
                        "found": notion_result.get('found', False),
                        "page_id": notion_result.get('page_id'),
                        "message": "Поиск страницы в Notion завершен успешно"
                    }
                else:
                    result = {
                        "status": "error",
                        "found": False,
                        "page_id": None,
                        "message": f"Ошибка поиска страницы в Notion: {notion_result.get('message', 'Unknown error')}"
                    }
                    
            except ImportError:
                self.logger.warning("⚠️ Модуль notion_templates не найден, используем заглушку")
                result = {
                    "status": "warning",
                    "found": False,
                    "page_id": None,
                    "message": "Модуль notion_templates не найден, поиск не выполнен"
                }
            except Exception as e:
                self.logger.error(f"❌ Ошибка поиска страницы в Notion: {e}")
                result = {
                    "status": "error",
                    "found": False,
                    "page_id": None,
                    "message": f"Ошибка поиска страницы в Notion: {str(e)}"
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
                    # Если время передано как строка, парсим его
                    if isinstance(start_dt, str):
                        from datetime import datetime
                        start_dt = datetime.fromisoformat(start_dt.replace('Z', '+00:00'))
                    if isinstance(end_dt, str):
                        end_dt = datetime.fromisoformat(end_dt.replace('Z', '+00:00'))
                    
                    # Убеждаемся, что datetime объекты имеют таймзону
                    if not start_dt.tzinfo:
                        start_dt = timezone.localize(start_dt)
                    if not end_dt.tzinfo:
                        end_dt = timezone.localize(end_dt)
                    
                    # Конвертируем в нашу таймзону
                    start_dt = start_dt.astimezone(timezone)
                    end_dt = end_dt.astimezone(timezone)
                    
                    properties['Date'] = {
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
            elif event_data.get('html_link'):
                properties['Meeting Link'] = {
                    "url": str(event_data['html_link'])
                }
            
            # Drive Folder (полный путь к папке)
            if event_data.get('folder_path'):
                properties['Drive Folder'] = {
                    "url": str(event_data['folder_path'])
                }
            
            # Event ID (важно для предотвращения дублирования)
            if event_data.get('id'):
                properties['Event ID'] = {
                    "rich_text": [
                        {
                            "text": {
                                "content": str(event_data['id'])
                            }
                        }
                    ]
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
            
            # Calendar (тип календаря)
            if event_data.get('account_type'):
                properties['Calendar'] = {
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


    def create_meeting_page(self, calendar_event, folder_path, account_type) -> Dict[str, Any]:
        """
        Создает страницу встречи в Notion по шаблону.
        
        Args:
            calendar_event: Событие календаря
            folder_path: Путь к папке встречи
            account_type: Тип аккаунта
            
        Returns:
            Результат создания страницы Notion
        """
        try:
            self.logger.info(f"📝 Создание страницы Notion для встречи: {calendar_event.get('title', 'Unknown')}")
            
            # Проверяем конфигурацию Notion
            if not self._validate_notion_config():
                return {"success": False, "message": "Notion configuration not valid"}
            
            # Подготавливаем данные для шаблона
            page_data = self._prepare_page_data(calendar_event, folder_path, account_type)
            
            # Создаем страницу через API Notion
            notion_page = self._create_notion_page(page_data)
            
            if notion_page:
                self.logger.info(f"✅ Страница Notion создана: {notion_page.get('id', 'unknown')}")
                return {
                    "success": True, 
                    "page_id": notion_page.get("id"),
                    "url": notion_page.get("url"),
                    "message": "Notion page created successfully"
                }
            else:
                return {"success": False, "message": "Failed to create Notion page"}
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания страницы Notion: {e}")
            return {"success": False, "message": str(e)}

    def update_meeting_results(self, notion_page_id, processing_results) -> Dict[str, Any]:
        """
        Обновляет страницу Notion результатами обработки.
        
        Args:
            notion_page_id: ID страницы Notion
            processing_results: Результаты обработки
            
        Returns:
            Результат обновления
        """
        try:
            self.logger.info(f"📝 Обновление страницы Notion {notion_page_id} результатами обработки")
            
            # Проверяем конфигурацию Notion
            if not self._validate_notion_config():
                return {"success": False, "message": "Notion configuration not valid"}
            
            if not notion_page_id:
                self.logger.error(f"❌ ID страницы Notion не предоставлен")
                return {"success": False, "message": "Notion page ID not provided"}
            
            # Обновляем контент страницы
            success = self._update_page_content(notion_page_id, processing_results)
            
            if success:
                self.logger.info(f"✅ Страница Notion {notion_page_id} успешно обновлена")
                return {"success": True, "message": "Notion page updated successfully"}
            else:
                self.logger.error(f"❌ Не удалось обновить страницу Notion {notion_page_id}")
                return {"success": False, "message": "Failed to update Notion page"}
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления страницы Notion: {e}")
            return {"success": False, "message": str(e)}

    def find_existing_meeting_page(self, event_data: Dict[str, Any], account_type: str) -> Optional[str]:
        """
        Ищет существующую страницу встречи в Notion.
        
        Args:
            event_data: Данные события
            account_type: Тип аккаунта
            
        Returns:
            ID существующей страницы или None
        """
        try:
            # Получаем конфигурацию Notion
            notion_config = self.config_manager.get_notion_config()
            notion_token = notion_config.get('token')
            database_id = notion_config.get('database_id')
            
            if not notion_token or not database_id:
                self.logger.warning("⚠️ Не настроена конфигурация Notion для поиска")
                return None
            
            # Создаем фильтры для поиска (в порядке приоритета)
            filters = []
            
            # 1. По Event ID (самый надежный способ, если ID есть в календаре)
            if event_data.get('id') and event_data.get('id') != 'unknown':
                filters.append({
                    "property": "Event ID",
                    "rich_text": {
                        "equals": str(event_data['id'])
                    }
                })
            
            # 2. По названию и типу календаря (fallback)
            if event_data.get('title'):
                filters.append({
                    "and": [
                        {
                            "property": "Name",
                            "title": {
                                "equals": event_data['title']
                            }
                        },
                        {
                            "property": "Calendar",
                            "select": {
                                "equals": account_type
                            }
                        }
                    ]
                })
            
            # Выполняем поиск
            for filter_config in filters:
                try:
                    from src.handlers.notion_api import NotionAPI
                    api = NotionAPI(self.config_manager)
                    
                    # Ищем страницы с текущим фильтром
                    search_result = api.search_pages(
                        database_id=database_id,
                        filter_config=filter_config,
                        max_results=5
                    )
                    
                    if search_result and search_result.get('results'):
                        page_id = search_result['results'][0]['id']
                        self.logger.info(f"✅ Найдена существующая страница: {page_id}")
                        return page_id
                        
                except Exception as e:
                    self.logger.warning(f"⚠️ Ошибка поиска с фильтром: {e}")
                    continue
            
            self.logger.info(f"🔍 Существующая страница для встречи '{event_data.get('title', 'Unknown')}' не найдена")
            return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска существующей страницы: {e}")
            return None
    
    def update_existing_meeting_page(self, page_id: str, event_data: Dict[str, Any], account_type: str) -> Dict[str, Any]:
        """
        Обновляет существующую страницу встречи в Notion.
        
        Args:
            page_id: ID существующей страницы
            event_data: Новые данные события
            account_type: Тип аккаунта
            
        Returns:
            Результат обновления
        """
        try:
            # Получаем конфигурацию Notion
            notion_config = self.config_manager.get_notion_config()
            notion_token = notion_config.get('token')
            
            if not notion_token:
                return {
                    "success": False,
                    "message": "Не настроена конфигурация Notion"
                }
            
            # Создаем только свойства для обновления (без содержимого)
            properties = self._create_meeting_properties(event_data, account_type)
            
            # Обновляем только свойства страницы
            from src.handlers.notion_api import NotionAPI
            api = NotionAPI(self.config_manager)
            
            update_result = api.update_page_properties(page_id, properties)
            
            if update_result:
                self.logger.info(f"✅ Свойства страницы {page_id} успешно обновлены")
                return {
                    "success": True,
                    "page_id": page_id,
                    "message": "Свойства страницы встречи обновлены"
                }
            else:
                return {
                    "success": False,
                    "message": "Не удалось обновить свойства страницы"
                }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления страницы {page_id}: {e}")
            return {
                "success": False,
                "message": f"Ошибка обновления: {e}"
            }

    def _prepare_page_data(self, event, folder_path, account_type) -> Dict[str, Any]:
        """
        Подготавливает данные для страницы по шаблону.
        
        Args:
            event: Событие календаря
            folder_path: Путь к папке встречи
            account_type: Тип аккаунта
            
        Returns:
            Данные для создания страницы
        """
        try:
            # Извлекаем данные из события
            title = event.get("title", "Unknown Event")
            start_time = event.get("start", "")
            end_time = event.get("end", "")
            attendees = event.get("attendees", [])
            
            # Формируем данные для шаблона
            page_data = {
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "attendees": attendees,
                "meeting_link": "",
                "drive_link": folder_path,
                "account_type": account_type
            }
            
            return page_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки данных страницы: {e}")
            return {}

    def _create_notion_page(self, page_data) -> Dict[str, Any]:
        """
        Создает страницу в Notion через API.
        
        Args:
            page_data: Данные для создания страницы
            
        Returns:
            Созданная страница Notion или None
        """
        try:
            # Используем notion_templates для создания страницы
            from notion_templates import create_meeting_page
            
            # Создаем страницу через notion_templates
            result = create_meeting_page(page_data, self.config_manager)
            
            if result and result.get('status') == 'success':
                page_id = result.get('page_id')
                self.logger.info(f"✅ Страница Notion успешно создана: {page_id}")
                
                return {
                    "id": page_id,
                    "url": f"https://notion.so/{page_id}",
                    "page_id": page_id,
                    "title": page_data.get("title", "Unknown"),
                    "created": datetime.now().isoformat()
                }
            else:
                self.logger.error(f"❌ Ошибка создания страницы Notion: {result.get('message', 'Unknown error')}")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания страницы через API Notion: {e}")
            return None

    def _prepare_page_properties(self, page_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготавливает свойства страницы для Notion.
        
        Args:
            page_data: Данные страницы
            
        Returns:
            Свойства страницы для Notion
        """
        try:
            properties = {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": page_data.get("title", "Unknown Event")
                            }
                        }
                    ]
                }
            }
            
            # Добавляем время встречи
            if page_data.get("start_time"):
                properties["Meeting Time"] = {
                    "date": {
                        "start": page_data.get("start_time"),
                        "end": page_data.get("end_time", "")
                    }
                }
            
            # Добавляем тип аккаунта
            if page_data.get("account_type"):
                properties["Account Type"] = {
                    "select": {
                        "name": page_data.get("account_type").title()
                    }
                }
            
            # Добавляем количество участников
            if page_data.get("attendees"):
                properties["Attendees Count"] = {
                    "number": len(page_data.get("attendees", []))
                }
            
            return properties
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки свойств страницы: {e}")
            return {}
    
    def _prepare_page_content(self, page_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Подготавливает содержимое страницы для Notion.
        
        Args:
            page_data: Данные страницы
            
        Returns:
            Содержимое страницы для Notion
        """
        try:
            content = []
            
            # Заголовок
            content.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"📋 {page_data.get('title', 'Unknown Event')}"
                            }
                        }
                    ]
                }
            })
            
            # Информация о времени
            if page_data.get("start_time"):
                start_time = page_data.get("start_time")
                end_time = page_data.get("end_time", "")
                time_text = f"⏰ {start_time}"
                if end_time:
                    time_text += f" - {end_time}"
                
                content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": time_text
                                }
                            }
                        ],
                        "icon": {
                            "type": "emoji",
                            "emoji": "⏰"
                        },
                        "color": "blue_background"
                    }
                })
            
            # Участники
            if page_data.get("attendees"):
                attendees_text = f"👥 Участники: {', '.join(page_data.get('attendees', []))}"
                content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": attendees_text
                                }
                            }
                        ],
                        "icon": {
                            "type": "emoji",
                            "emoji": "👥"
                        },
                        "color": "yellow_background"
                    }
                })
            
            # Разделитель
            content.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Раздел для материалов встречи
            content.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📁 Материалы встречи"
                            }
                        }
                    ]
                }
            })
            
            content.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Здесь будут размещены материалы встречи после обработки."
                            }
                        }
                    ]
                }
            })
            
            # Раздел для результатов
            content.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📊 Результаты обработки"
                            }
                        }
                    ]
                }
            })
            
            content.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Здесь будут размещены результаты обработки материалов встречи."
                            }
                        }
                    ]
                }
            })
            
            return content
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки содержимого страницы: {e}")
            return []

    def _prepare_update_properties(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Подготавливает свойства для обновления страницы.
        
        Args:
            results: Результаты обработки
            
        Returns:
            Свойства для обновления
        """
        try:
            properties = {}
            
            # Статус обработки
            if results.get("status"):
                properties["Processing Status"] = {
                    "select": {
                        "name": results.get("status").title()
                    }
                }
            
            # Количество обработанных файлов
            if results.get("files_processed"):
                properties["Files Processed"] = {
                    "number": results.get("files_processed", 0)
                }
            
            # Время обработки
            if results.get("processing_time"):
                properties["Processing Time"] = {
                    "number": results.get("processing_time", 0)
                }
            
            # Дата последнего обновления
            properties["Last Updated"] = {
                "date": {
                    "start": datetime.now().isoformat()
                }
            }
            
            return properties
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки свойств для обновления: {e}")
            return {}
    
    def _prepare_update_content(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Подготавливает содержимое для обновления страницы.
        
        Args:
            results: Результаты обработки
            
        Returns:
            Содержимое для обновления
        """
        try:
            content = []
            
            # Раздел результатов обработки
            content.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📊 Результаты обработки"
                            }
                        }
                    ]
                }
            })
            
            # Статус обработки
            if results.get("status"):
                status_text = f"✅ Статус: {results.get('status')}"
                content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": status_text
                                }
                            }
                        ],
                        "icon": {
                            "type": "emoji",
                            "emoji": "✅"
                        },
                        "color": "green_background"
                    }
                })
            
            # Обработанные файлы
            if results.get("files_processed"):
                files_text = f"📁 Обработано файлов: {results.get('files_processed')}"
                content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": files_text
                                }
                            }
                        ],
                        "icon": {
                            "type": "emoji",
                            "emoji": "📁"
                        },
                        "color": "blue_background"
                    }
                })
            
            # Время обработки
            if results.get("processing_time"):
                time_text = f"⏱️ Время обработки: {results.get('processing_time')} секунд"
                content.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": time_text
                                }
                            }
                        ],
                        "icon": {
                            "type": "emoji",
                            "emoji": "⏱️"
                        },
                        "color": "yellow_background"
                    }
                })
            
            # Детали обработки
            if results.get("details"):
                content.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "📋 Детали обработки"
                                }
                            }
                        ]
                    }
                })
                
                for detail in results.get("details", []):
                    content.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": detail
                                    }
                                }
                            ]
                        }
                    })
            
            return content
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка подготовки содержимого для обновления: {e}")
            return []

    def _update_page_content(self, page_id: str, processing_results: Dict[str, Any]) -> bool:
        """
        Обновляет контент страницы Notion результатами обработки.
        
        Args:
            page_id: ID страницы Notion
            processing_results: Результаты обработки
            
        Returns:
            True если обновление успешно, False иначе
        """
        try:
            self.logger.info(f"📝 Обновление контента страницы {page_id}")
            
            # Получаем конфигурацию Notion
            notion_config = self.config_manager.get_notion_config()
            notion_token = notion_config.get('token')
            
            if not notion_token:
                self.logger.error("❌ Не настроен Notion токен")
                return False
            
            # Подготавливаем блоки для добавления
            blocks_to_add = []
            
            # Добавляем транскрипцию если есть
            if processing_results.get('transcription'):
                transcript_data = processing_results['transcription']
                if transcript_data.get('status') == 'success' and transcript_data.get('file_path'):
                    transcript_blocks = self._create_transcript_blocks(transcript_data['file_path'])
                    blocks_to_add.extend(transcript_blocks)
            
            # Добавляем саммари если есть
            if processing_results.get('summary'):
                summary_data = processing_results['summary']
                if summary_data.get('status') == 'success' and summary_data.get('file_path'):
                    summary_blocks = self._create_summary_blocks(summary_data['file_path'])
                    blocks_to_add.extend(summary_blocks)
            
            # Если есть блоки для добавления, добавляем их
            if blocks_to_add:
                success = self._add_blocks_to_page(page_id, blocks_to_add, notion_token)
                if success:
                    self.logger.info(f"✅ Контент страницы {page_id} успешно обновлен")
                    
                    # Записываем статус синхронизации в БД
                    self._record_content_sync_status(page_id, processing_results, "success")
                    return True
                else:
                    self.logger.error(f"❌ Не удалось обновить контент страницы {page_id}")
                    self._record_content_sync_status(page_id, processing_results, "error", "Failed to add blocks to page")
                    return False
            else:
                self.logger.info(f"ℹ️ Нет нового контента для добавления на страницу {page_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления контента страницы {page_id}: {e}")
            return False

    def _create_transcript_blocks(self, transcript_file_path: str) -> List[Dict[str, Any]]:
        """Создает блоки для транскрипции."""
        try:
            blocks = []
            
            # Заголовок транскрипции
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📝 Транскрипция встречи"}}]
                }
            })
            
            # Читаем файл транскрипции
            if os.path.exists(transcript_file_path):
                with open(transcript_file_path, 'r', encoding='utf-8') as f:
                    transcript_content = f.read()
                
                # Разбиваем на части (лимит Notion - 2000 символов на блок)
                chunk_size = 1800
                transcript_chunks = [transcript_content[i:i+chunk_size] for i in range(0, len(transcript_content), chunk_size)]
                
                for chunk in transcript_chunks:
                    blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })
            
            return blocks
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания блоков транскрипции: {e}")
            return []

    def _create_summary_blocks(self, summary_file_path: str) -> List[Dict[str, Any]]:
        """Создает блоки для саммари."""
        try:
            blocks = []
            
            # Заголовок саммари
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 Саммари встречи"}}]
                }
            })
            
            # Читаем файл саммари
            if os.path.exists(summary_file_path):
                with open(summary_file_path, 'r', encoding='utf-8') as f:
                    summary_content = f.read()
                
                # Разбиваем на части
                chunk_size = 1800
                summary_chunks = [summary_content[i:i+chunk_size] for i in range(0, len(summary_content), chunk_size)]
                
                for chunk in summary_chunks:
                    blocks.append({
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": chunk}}]
                        }
                    })
            
            return blocks
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания блоков саммари: {e}")
            return []

    def _add_blocks_to_page(self, page_id: str, blocks: List[Dict[str, Any]], notion_token: str) -> bool:
        """Добавляет блоки на страницу Notion."""
        try:
            import requests
            
            headers = {
                'Authorization': f'Bearer {notion_token}',
                'Notion-Version': '2022-06-28',
                'Content-Type': 'application/json'
            }
            
            # Добавляем блоки по частям (лимит API)
            chunk_size = 50
            for i in range(0, len(blocks), chunk_size):
                chunk = blocks[i:i+chunk_size]
                
                url = f'https://api.notion.com/v1/blocks/{page_id}/children'
                payload = {'children': chunk}
                
                response = requests.patch(url, headers=headers, json=payload)
                
                if response.status_code != 200:
                    self.logger.error(f"❌ Ошибка добавления блоков: {response.status_code} - {response.text}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка добавления блоков на страницу: {e}")
            return False

    def _record_content_sync_status(self, page_id: str, processing_results: Dict[str, Any], status: str, error_message: str = None):
        """Записывает статус синхронизации контента в БД."""
        try:
            if not self.state_manager:
                return
            
            # Получаем event_id по page_id
            event_id = self._get_event_id_by_page_id(page_id)
            if not event_id:
                self.logger.warning(f"⚠️ Не удалось найти event_id для page_id {page_id}")
                return
            
            # Записываем статус для каждого типа контента
            if processing_results.get('transcription'):
                self.state_manager.record_content_sync_status(
                    event_id, 'transcription', status, error_message
                )
            
            if processing_results.get('summary'):
                self.state_manager.record_content_sync_status(
                    event_id, 'summary', status, error_message
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка записи статуса синхронизации: {e}")

    def _get_event_id_by_page_id(self, page_id: str) -> Optional[str]:
        """Получает event_id по page_id из БД."""
        try:
            if not self.state_manager:
                return None
            
            with sqlite3.connect(self.state_manager.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT event_id FROM notion_sync_status 
                    WHERE page_id = ?
                ''', (page_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения event_id для page_id {page_id}: {e}")
            return None
