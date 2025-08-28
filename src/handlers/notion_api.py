#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API клиент для работы с Notion
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import requests


class NotionAPI:
    """API клиент для работы с Notion."""
    
    def __init__(self, config_manager, logger=None):
        """
        Инициализация API клиента Notion.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
        self.base_url = "https://api.notion.com/v1"
        self.headers = self._setup_headers()
        
    def _setup_headers(self) -> Dict[str, str]:
        """
        Настраивает заголовки для API запросов.
        
        Returns:
            Словарь заголовков
        """
        notion_config = self.config_manager.get_notion_config()
        token = notion_config.get('token')
        
        if not token:
            self.logger.warning("⚠️ Токен Notion не настроен")
            return {}
        
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
    
    def create_page(self, parent_id: str, title: str, properties: Dict[str, Any] = None, content: List[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Создает новую страницу в Notion.
        
        Args:
            parent_id: ID родительской страницы или базы данных
            title: Заголовок страницы
            properties: Свойства страницы
            content: Содержимое страницы (блоки)
            
        Returns:
            Созданная страница или None
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return None
            
            # Подготавливаем данные для создания страницы
            page_data = {
                "parent": {"page_id": parent_id} if parent_id.startswith('page_') else {"database_id": parent_id},
                "properties": properties or {},
                "children": content or []
            }
            
            # Создаем страницу
            response = requests.post(
                f"{self.base_url}/pages",
                headers=self.headers,
                json=page_data,
                timeout=30
            )
            
            if response.status_code == 200:
                page = response.json()
                self.logger.info(f"✅ Страница Notion создана: {page.get('id', 'unknown')}")
                return page
            else:
                self.logger.error(f"❌ Ошибка создания страницы Notion: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания страницы Notion: {e}")
            return None
    
    def update_page(self, page_id: str, properties: Dict[str, Any] = None, content: List[Dict[str, Any]] = None) -> bool:
        """
        Обновляет существующую страницу в Notion.
        
        Args:
            page_id: ID страницы для обновления
            properties: Новые свойства страницы
            content: Новое содержимое страницы
            
        Returns:
            True если обновление успешно, False иначе
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return False
            
            # Подготавливаем данные для обновления
            update_data = {}
            if properties:
                update_data["properties"] = properties
            if content:
                update_data["children"] = content
            
            if not update_data:
                self.logger.warning("⚠️ Нет данных для обновления")
                return True
            
            # Обновляем страницу
            response = requests.patch(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                self.logger.info(f"✅ Страница Notion обновлена: {page_id}")
                return True
            else:
                self.logger.error(f"❌ Ошибка обновления страницы Notion: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления страницы Notion: {e}")
            return False
    
    def get_page(self, page_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает страницу из Notion.
        
        Args:
            page_id: ID страницы
            
        Returns:
            Страница или None
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return None
            
            response = requests.get(
                f"{self.base_url}/pages/{page_id}",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                self.logger.error(f"❌ Ошибка получения страницы Notion: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения страницы Notion: {e}")
            return None
    
    def search_pages(self, query: str = "", filter_type: str = "page") -> List[Dict[str, Any]]:
        """
        Ищет страницы в Notion.
        
        Args:
            query: Поисковый запрос
            filter_type: Тип фильтра (page, database)
            
        Returns:
            Список найденных страниц
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return []
            
            search_data = {
                "filter": {
                    "value": filter_type,
                    "property": "object"
                }
            }
            
            if query:
                search_data["query"] = query
            
            response = requests.post(
                f"{self.base_url}/search",
                headers=self.headers,
                json=search_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("results", [])
            else:
                self.logger.error(f"❌ Ошибка поиска в Notion: {response.status_code} - {response.text}")
                return []
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска в Notion: {e}")
            return []
    
    def create_database(self, parent_id: str, title: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Создает новую базу данных в Notion.
        
        Args:
            parent_id: ID родительской страницы
            title: Название базы данных
            properties: Свойства базы данных
            
        Returns:
            Созданная база данных или None
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return None
            
            database_data = {
                "parent": {"page_id": parent_id},
                "title": [{"text": {"content": title}}],
                "properties": properties
            }
            
            response = requests.post(
                f"{self.base_url}/databases",
                headers=self.headers,
                json=database_data,
                timeout=30
            )
            
            if response.status_code == 200:
                database = response.json()
                self.logger.info(f"✅ База данных Notion создана: {database.get('id', 'unknown')}")
                return database
            else:
                self.logger.error(f"❌ Ошибка создания базы данных Notion: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания базы данных Notion: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Тестирует соединение с Notion API.
        
        Returns:
            True если соединение успешно, False иначе
        """
        try:
            if not self.headers:
                self.logger.error("❌ Заголовки API не настроены")
                return False
            
            # Пытаемся получить информацию о пользователе
            response = requests.get(
                f"{self.base_url}/users/me",
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                user_info = response.json()
                self.logger.info(f"✅ Соединение с Notion успешно: {user_info.get('name', 'Unknown')}")
                return True
            else:
                self.logger.error(f"❌ Ошибка соединения с Notion: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка соединения с Notion: {e}")
            return False
