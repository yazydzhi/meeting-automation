"""
Модуль для работы с Notion API
"""

import os
import requests
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class NotionAPI:
    """Класс для работы с Notion API"""
    
    def __init__(self, token: str, database_id: str):
        """
        Инициализация API
        
        Args:
            token: Токен Notion API
            database_id: ID базы данных
        """
        self.token = token
        self.database_id = database_id
        self.base_url = "https://api.notion.com/v1"
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def search_page_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Ищет страницу по названию
        
        Args:
            title: Название страницы
            
        Returns:
            Данные страницы или None
        """
        try:
            logger.info(f"🔍 Ищем страницу: {title}")
            
            query = {
                "filter": {
                    "property": "Name",
                    "title": {
                        "contains": title
                    }
                }
            }
            
            response = requests.post(
                f'{self.base_url}/databases/{self.database_id}/query',
                headers=self.headers,
                json=query
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    logger.info(f"✅ Найдено страниц: {len(results)}")
                    return results[0]  # Возвращаем первую найденную
                else:
                    logger.info("❌ Страница не найдена")
                    return None
            else:
                logger.error(f"❌ Ошибка поиска: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка поиска страницы: {e}")
            return None
    
    def add_content_to_page(self, page_id: str, content_data: Dict[str, Any]) -> bool:
        """
        Добавляет контент на страницу
        
        Args:
            page_id: ID страницы
            content_data: Данные для добавления (из TranscriptAnalyzer)
            
        Returns:
            True если успешно
        """
        try:
            logger.info(f"📝 Добавляю контент на страницу: {page_id}")
            
            # Получаем существующие блоки
            existing_blocks = self.get_page_blocks(page_id)
            
            # Создаем новые блоки на основе анализа
            new_blocks = self.create_content_blocks(content_data)
            
            # Добавляем новые блоки
            if new_blocks:
                response = requests.patch(
                    f'{self.base_url}/blocks/{page_id}/children',
                    headers=self.headers,
                    json={'children': new_blocks}
                )
                
                if response.status_code == 200:
                    logger.info("✅ Контент успешно добавлен на страницу")
                    return True
                else:
                    logger.error(f"❌ Ошибка добавления контента: {response.status_code}")
                    logger.error(f"📄 Ответ: {response.text}")
                    return False
            else:
                logger.warning("⚠️ Нет контента для добавления")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка добавления контента: {e}")
            return False
    
    def get_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        """
        Получает существующие блоки страницы
        
        Args:
            page_id: ID страницы
            
        Returns:
            Список блоков
        """
        try:
            response = requests.get(
                f'{self.base_url}/blocks/{page_id}/children',
                headers=self.headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
            else:
                logger.error(f"❌ Ошибка получения блоков: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка получения блоков: {e}")
            return []
    
    def create_content_blocks(self, content_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Создает блоки контента на основе анализа
        
        Args:
            content_data: Данные анализа от TranscriptAnalyzer
            
        Returns:
            Список блоков для Notion
        """
        blocks = []
        
        try:
            # Добавляем разделитель
            blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # Добавляем заголовок анализа
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "🤖 Анализ транскрипции"
                            }
                        }
                    ]
                }
            })
            
            # Добавляем основную информацию
            summary = content_data.get('meeting_summary', {})
            if summary.get('main_topic'):
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {"type": "emoji", "emoji": "🎯"},
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Основная тема: {summary['main_topic']}"
                                }
                            }
                        ]
                    }
                })
            
            # Добавляем действия
            action_items = summary.get('action_items', [])
            if action_items:
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "📋 Действия"
                                }
                            }
                        ]
                    }
                })
                
                for action in action_items:
                    blocks.append({
                        "object": "block",
                        "type": "to_do",
                        "to_do": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": action
                                    }
                                }
                            ]
                        }
                    })
            
            # Добавляем темы обсуждения
            topics = content_data.get('topics_discussed', [])
            if topics:
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "💬 Темы обсуждения"
                                }
                            }
                        ]
                    }
                })
                
                for topic in topics:
                    blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": topic.get('topic', 'Тема')
                                    }
                                }
                            ]
                        }
                    })
                    
                    if topic.get('description'):
                        blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [
                                    {
                                        "type": "text",
                                        "text": {
                                            "content": topic['description']
                                        }
                                    }
                                ]
                            }
                        })
            
            # Добавляем ключевые цитаты
            quotes = content_data.get('key_quotes', [])
            if quotes:
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "💬 Ключевые цитаты"
                                }
                            }
                        ]
                    }
                })
                
                for quote in quotes:
                    blocks.append({
                        "object": "block",
                        "type": "quote",
                        "quote": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"\"{quote.get('quote', '')}\" — {quote.get('speaker', 'Неизвестно')}"
                                    }
                                }
                            ]
                        }
                    })
            
            # Добавляем финансовую информацию
            financial = content_data.get('financial_mentions', [])
            if financial:
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "💰 Финансовая информация"
                                }
                            }
                        ]
                    }
                })
                
                for item in financial:
                    blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": f"{item.get('amount', '')} - {item.get('context', '')}"
                                    }
                                }
                            ]
                        }
                    })
            
            # Добавляем метаданные анализа
            metadata = content_data.get('analysis_metadata', {})
            if metadata:
                blocks.append({
                    "object": "block",
                    "type": "divider",
                    "divider": {}
                })
                
                blocks.append({
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {"type": "emoji", "emoji": "🤖"},
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": f"Анализ выполнен: {metadata.get('analyzed_at', 'Неизвестно')} | Модель: {metadata.get('model_used', 'Неизвестно')}"
                                }
                            }
                        ]
                    }
                })
            
            logger.info(f"✅ Создано {len(blocks)} блоков контента")
            return blocks
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания блоков: {e}")
            return []
    
    def update_page_properties(self, page_id: str, properties: Dict[str, Any]) -> bool:
        """
        Обновляет свойства страницы
        
        Args:
            page_id: ID страницы
            properties: Новые свойства
            
        Returns:
            True если успешно
        """
        try:
            logger.info(f"🔄 Обновляю свойства страницы: {page_id}")
            
            response = requests.patch(
                f'{self.base_url}/pages/{page_id}',
                headers=self.headers,
                json={'properties': properties}
            )
            
            if response.status_code == 200:
                logger.info("✅ Свойства страницы обновлены")
                return True
            else:
                logger.error(f"❌ Ошибка обновления свойств: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка обновления свойств: {e}")
            return False
