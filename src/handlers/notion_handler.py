#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для синхронизации с Notion
"""

from typing import Dict, Any, List
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
                    result = {
                        "status": "success",
                        "page_id": notion_result.get('page_id', 'unknown'),
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
            
            # Обновляем страницу через Notion API
            notion_config = self.config_manager.get_notion_config()
            
            # Ищем страницу по ID события или пути папки
            page_id = self._get_notion_page_id_by_event_id(event_id) or \
                      self._get_notion_page_id_by_folder_path(folder_path)
            
            if not page_id:
                self.logger.error(f"❌ Страница Notion для события {event_id} не найдена")
                return False
            
            # Подготавливаем свойства для обновления
            properties = self._prepare_update_properties(results)
            
            # Подготавливаем содержимое для обновления
            content = self._prepare_update_content(results)
            
            # Обновляем страницу
            success = self.notion_api.update_page(page_id, properties, content)
            
            return success
            # Пока возвращаем заглушку
            self.logger.info(f"📝 Обновление страницы Notion (заглушка): {processing_results}")
            
            return {
                "success": True,
                "message": "Notion page update not yet implemented"
            }
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления страницы Notion: {e}")
            return {"success": False, "message": str(e)}

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
