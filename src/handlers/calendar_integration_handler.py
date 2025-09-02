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
        
        # Отладочная информация
        if calendar_handler:
            self.logger.info(f"📅 Используем переданный calendar_handler: {type(calendar_handler).__name__}")
            self.calendar_handler = calendar_handler
        else:
            self.logger.info("📅 Создаем новый CalendarHandler")
            self.calendar_handler = CalendarHandler(config_manager, logger)
            self.logger.info(f"📅 CalendarHandler создан: {type(self.calendar_handler).__name__}")
        
        self.calendar_events_cache = {}
        self.folder_notion_mapping = {}
        
        # Инициализируем StateManager для отслеживания обработанных событий
        try:
            from .state_manager import StateManager
            self.state_manager = StateManager(logger=self.logger)
            self.logger.info("✅ StateManager инициализирован в CalendarIntegrationHandler")
        except ImportError:
            self.state_manager = None
            self.logger.warning("⚠️ StateManager недоступен, используем старый кэш")
            # Загружаем кэш из файла
            self._load_events_cache()
    
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
            skipped_events = 0
            
            for event in calendar_events:
                try:
                    event_result = self._process_single_event(event, account_type)
                    if event_result['status'] == 'success':
                        processed_events += 1
                        if event_result.get('folder_created'):
                            created_folders += 1
                        if event_result.get('notion_page_created'):
                            created_notion_pages += 1
                    elif event_result['status'] == 'skipped':
                        # Событие уже обработано - это нормально, не ошибка
                        skipped_events += 1
                        self.logger.info(f"⏭️ Событие {event.get('title', 'Unknown')} пропущено: {event_result.get('message', 'Already processed')}")
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
                "skipped": skipped_events,
                "details": [
                    f"Обработано событий: {processed_events}",
                    f"Создано папок: {created_folders}",
                    f"Создано страниц Notion: {created_notion_pages}",
                    f"Ошибок: {errors}",
                    f"Пропущено событий: {skipped_events}"
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
                events = self.calendar_handler.get_calendar_events(account_type)
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
            notion_result = self._create_notion_page(event, account_type)
            if not notion_result['success']:
                self.logger.warning(f"⚠️ Не удалось создать страницу Notion для {event_title}: {notion_result['message']}")
                # Продолжаем работу, так как папка создана
            
            # Помечаем событие как обработанное
            event_title = event.get('title', 'Unknown Event')
            event_start_time = event.get('start', '')
            event_end_time = event.get('end', '')
            self._mark_event_processed(event_id, account_type, event_title, event_start_time, event_end_time)
            
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
            
            # Помечаем папку как созданную в БД
            if self.state_manager and event.get('id'):
                self.state_manager.mark_folder_created(
                    event['id'], 
                    folder_path, 
                    account_type, 
                    "success"
                )
            
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
    
    def _create_notion_page(self, event: Dict[str, Any], account_type: str) -> Dict[str, Any]:
        """
        Создает или обновляет страницу в Notion для события.
        Сначала проверяет существование страницы, чтобы избежать дублирования.
        
        Args:
            event: Событие календаря
            account_type: Тип аккаунта
            
        Returns:
            Результат создания/обновления страницы Notion
        """
        try:
            if not self.notion_handler:
                return {"success": False, "message": "Notion handler not available"}
            
            # Сначала проверяем, существует ли уже страница для этой встречи
            existing_page_id = self.notion_handler.find_existing_meeting_page(event, account_type)
            
            if existing_page_id:
                # Страница уже существует - обновляем её свойства
                self.logger.info(f"🔄 Страница для встречи '{event.get('title', 'Unknown')}' уже существует, обновляю свойства")
                
                update_result = self.notion_handler.update_existing_meeting_page(existing_page_id, event, account_type)
                
                if update_result.get('success'):
                    # Помечаем событие как синхронизированное с Notion в БД
                    if self.state_manager and event.get('id'):
                        self.state_manager.mark_notion_synced(
                            event['id'], 
                            existing_page_id, 
                            update_result.get('page_url', ''), 
                            "success"
                        )
                    
                    return {
                        "success": True,
                        "page_id": existing_page_id,
                        "message": "Existing Notion page updated successfully",
                        "updated": True
                    }
                else:
                    self.logger.warning(f"⚠️ Не удалось обновить существующую страницу: {update_result.get('message')}")
                    # Продолжаем с созданием новой страницы
            
            # Создаем новую страницу
            self.logger.info(f"📄 Создаю новую страницу в Notion для встречи '{event.get('title', 'Unknown')}'")
            
            page_data = self.notion_handler._prepare_page_data(event, "", account_type)
            notion_page = self.notion_handler._create_notion_page(page_data)
            
            if notion_page:
                page_id = notion_page.get('page_id')
                self.logger.info(f"✅ Страница Notion создана для {event.get('title', 'Unknown')}: {page_id}")
                
                # Помечаем событие как синхронизированное с Notion в БД
                if self.state_manager and event.get('id'):
                    self.state_manager.mark_notion_synced(
                        event['id'], 
                        page_id, 
                        notion_page.get('url', ''), 
                        "success"
                    )
                
                return {
                    "success": True,
                    "page_id": page_id,
                    "message": "Notion page created successfully",
                    "updated": False
                }
            else:
                self.logger.error(f"❌ Не удалось создать страницу Notion для {event.get('title', 'Unknown')}")
                return {"success": False, "message": "Failed to create Notion page"}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания/обновления страницы Notion: {e}")
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
            # Используем StateManager если доступен
            if self.state_manager:
                return self.state_manager.is_event_processed(event_id, account_type)
            else:
                # Fallback на старый кэш
                cache_key = f"{account_type}_{event_id}"
                return cache_key in self.calendar_events_cache
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки статуса события: {e}")
            return False
    
    def _mark_event_processed(self, event_id: str, account_type: str, event_title: str = "", 
                            event_start_time: str = "", event_end_time: str = ""):
        """
        Помечает событие как обработанное.
        
        Args:
            event_id: ID события
            account_type: Тип аккаунта
            event_title: Название события
            event_start_time: Время начала события
            event_end_time: Время окончания события
        """
        try:
            # Используем StateManager если доступен
            if self.state_manager:
                self.state_manager.mark_event_processed(event_id, account_type, event_title, 
                                                      event_start_time, event_end_time)
            else:
                # Fallback на старый кэш
                cache_key = f"{account_type}_{event_id}"
                self.calendar_events_cache[cache_key] = {
                    "processed_at": datetime.now().isoformat(),
                    "account_type": account_type
                }
                # Сохраняем кэш в файл
                self._save_events_cache()
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
    
    def _get_cache_file_path(self) -> str:
        """Возвращает путь к файлу кэша событий."""
        cache_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, 'calendar_events_cache.json')
    
    def _load_events_cache(self):
        """Загружает кэш событий из файла."""
        try:
            cache_file = self._get_cache_file_path()
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.calendar_events_cache = json.load(f)
                    self.logger.info(f"📋 Загружен кэш событий: {len(self.calendar_events_cache)} записей")
            else:
                self.logger.info("📋 Файл кэша событий не найден, создаем новый")
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка загрузки кэша событий: {e}, создаем новый")
            self.calendar_events_cache = {}
    
    def _save_events_cache(self):
        """Сохраняет кэш событий в файл."""
        try:
            cache_file = self._get_cache_file_path()
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.calendar_events_cache, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"📋 Кэш событий сохранен: {len(self.calendar_events_cache)} записей")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения кэша событий: {e}")
