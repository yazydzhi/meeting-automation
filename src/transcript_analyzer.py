"""
Модуль для анализа транскрипции встреч через OpenAI API.
Создает структурированные данные для заполнения страниц в Notion.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from openai import OpenAI


class TranscriptAnalyzer:
    """Анализатор транскрипции встреч через OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Инициализация анализатора
        
        Args:
            api_key: OpenAI API ключ
            model: Модель GPT для анализа
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.logger = logging.getLogger(__name__)
        
    def analyze_meeting_transcript(
        self, 
        transcript: str, 
        meeting_title: str = "",
        meeting_date: str = ""
    ) -> Dict[str, Any]:
        """
        Анализирует транскрипцию встречи и создает структурированные данные
        
        Args:
            transcript: Текст транскрипции
            meeting_title: Название встречи
            meeting_date: Дата встречи
            
        Returns:
            Словарь с проанализированными данными
        """
        try:
            self.logger.info("🔍 Начинаю анализ транскрипции через OpenAI...")
            
            # Создаем промпт для анализа
            prompt = self._create_analysis_prompt(transcript, meeting_title, meeting_date)
            
            # Отправляем запрос к OpenAI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - эксперт по анализу деловых встреч. Твоя задача - проанализировать транскрипцию и создать структурированные данные для заполнения страницы в Notion."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            # Получаем ответ
            analysis_text = response.choices[0].message.content
            self.logger.info("✅ Анализ завершен успешно")
            self.logger.info(f"📝 Получен ответ от OpenAI: {analysis_text[:200]}...")
            
            # Пытаемся извлечь JSON из ответа
            analysis_data = self._extract_json_from_response(analysis_text)
            
            # Добавляем метаданные
            analysis_data['analysis_metadata'] = {
                'analyzed_at': datetime.now().isoformat(),
                'model_used': self.model,
                'meeting_title': meeting_title,
                'meeting_date': meeting_date,
                'transcript_length': len(transcript)
            }
            
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка анализа транскрипции: {e}")
            return self._create_fallback_analysis(transcript, meeting_title, meeting_date)
    
    def _create_analysis_prompt(self, transcript: str, meeting_title: str, meeting_date: str) -> str:
        """Создает промпт для анализа транскрипции"""
        
        prompt = f"""
Проанализируй следующую транскрипцию деловой встречи и создай структурированные данные в формате JSON.

Название встречи: {meeting_title}
Дата встречи: {meeting_date}

ТРАНСКРИПЦИЯ:
{transcript}

Создай JSON с следующей структурой:

{{
    "meeting_summary": {{
        "title": "Краткое название встречи",
        "main_topic": "Основная тема обсуждения",
        "key_decisions": ["Ключевые решения", "..."],
        "action_items": ["Действия", "..."],
        "next_steps": ["Следующие шаги", "..."],
        "participants": ["Участники встречи", "..."],
        "duration_minutes": "Примерная длительность в минутах"
    }},
    "topics_discussed": [
        {{
            "topic": "Название темы",
            "description": "Описание обсуждения",
            "decisions": ["Принятые решения"],
            "action_items": ["Действия по теме"],
            "participants_involved": ["Участники, активно обсуждавшие тему"]
        }}
    ],
    "key_quotes": [
        {{
            "quote": "Важная цитата",
            "speaker": "Кто сказал",
            "context": "Контекст высказывания"
        }}
    ],
    "financial_mentions": [
        {{
            "amount": "Сумма или диапазон",
            "context": "Контекст упоминания",
            "type": "Тип (бюджет, доход, расход, инвестиции)"
        }}
    ],
    "deadlines": [
        {{
            "deadline": "Срок",
            "description": "Описание задачи",
            "responsible": "Ответственный"
        }}
    ],
    "risks_issues": [
        {{
            "type": "Тип (риск/проблема)",
            "description": "Описание",
            "severity": "Важность (высокая/средняя/низкая)",
            "mitigation": "Способы решения"
        }}
    ],
    "success_metrics": [
        {{
            "metric": "Метрика успеха",
            "target": "Целевое значение",
            "current_status": "Текущий статус"
        }}
    ]
}}

ВАЖНО:
1. Анализируй только то, что явно упоминается в транскрипции
2. Если информация отсутствует, используй null или пустые массивы
3. Сохраняй контекст и детали обсуждения
4. Используй русский язык для всех полей
5. Возвращай только валидный JSON без дополнительного текста
"""
        
        return prompt
    
    def _extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """Извлекает JSON из ответа OpenAI"""
        try:
            # Пытаемся найти JSON в ответе
            import re
            
            # Ищем JSON блок
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                self.logger.info(f"🔍 Найден JSON блок: {json_text[:100]}...")
                return json.loads(json_text)
            
            # Если JSON не найден, пытаемся парсить весь ответ
            self.logger.warning("⚠️ JSON блок не найден, пытаюсь парсить весь ответ")
            return json.loads(response_text)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"❌ Ошибка парсинга JSON: {e}")
            self.logger.error(f"📝 Ответ OpenAI: {response_text}")
            
            # Возвращаем базовую структуру с ошибкой
            return {
                "meeting_summary": {
                    "title": "Ошибка анализа",
                    "main_topic": "Не удалось проанализировать транскрипцию",
                    "key_decisions": [],
                    "action_items": [],
                    "next_steps": [],
                    "participants": [],
                    "duration_minutes": None
                },
                "topics_discussed": [],
                "key_quotes": [],
                "financial_mentions": [],
                "deadlines": [],
                "risks_issues": [],
                "success_metrics": [],
                "parsing_error": str(e),
                "raw_response": response_text[:500]
            }
    
    def _create_fallback_analysis(self, transcript: str, meeting_title: str, meeting_date: str) -> Dict[str, Any]:
        """Создает базовый анализ при ошибке OpenAI API"""
        
        self.logger.warning("⚠️ Создаю базовый анализ из-за ошибки OpenAI API")
        
        return {
            "meeting_summary": {
                "title": meeting_title or "Встреча",
                "main_topic": "Анализ не удался",
                "key_decisions": [],
                "action_items": [],
                "next_steps": [],
                "participants": [],
                "duration_minutes": None
            },
            "topics_discussed": [],
            "key_quotes": [],
            "financial_mentions": [],
            "deadlines": [],
            "risks_issues": [],
            "success_metrics": [],
            "analysis_metadata": {
                "analyzed_at": datetime.now().isoformat(),
                "model_used": "fallback",
                "meeting_title": meeting_title,
                "meeting_date": meeting_date,
                "transcript_length": len(transcript),
                "error": "OpenAI API недоступен"
            }
        }
    
    def create_notion_page_data(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Создает данные для страницы Notion на основе анализа
        
        Args:
            analysis_data: Результат анализа транскрипции
            
        Returns:
            Словарь с данными для создания страницы в Notion
        """
        try:
            self.logger.info("📝 Создаю данные для страницы Notion...")
            
            # Извлекаем основную информацию
            summary = analysis_data.get('meeting_summary', {})
            topics = analysis_data.get('topics_discussed', [])
            
            # Создаем структуру страницы
            page_data = {
                "properties": {
                    "Title": {
                        "title": [
                            {
                                "text": {
                                    "content": summary.get('title', 'Встреча')
                                }
                            }
                        ]
                    },
                    "Main Topic": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": summary.get('main_topic', 'Не указано')
                                }
                            }
                        ]
                    },
                    "Status": {
                        "select": {
                            "name": "Completed"
                        }
                    },
                    "Date": {
                        "date": {
                            "start": datetime.now().isoformat()
                        }
                    }
                },
                "children": []
            }
            
            # Добавляем заголовок
            page_data["children"].append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"📋 {summary.get('title', 'Встреча')}"
                            }
                        }
                    ]
                }
            })
            
            # Добавляем основную информацию
            if summary.get('main_topic'):
                page_data["children"].append({
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
            
            # Добавляем ключевые решения
            if summary.get('key_decisions'):
                page_data["children"].append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [
                            {
                                "type": "text",
                                "text": {
                                    "content": "✅ Ключевые решения"
                                }
                            }
                        ]
                    }
                })
                
                for decision in summary['key_decisions']:
                    page_data["children"].append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [
                                {
                                    "type": "text",
                                    "text": {
                                        "content": decision
                                    }
                                }
                            ]
                        }
                    })
            
            # Добавляем действия
            if summary.get('action_items'):
                page_data["children"].append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
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
                
                for action in summary['action_items']:
                    page_data["children"].append({
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
            if topics:
                page_data["children"].append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
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
                    page_data["children"].append({
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
                        page_data["children"].append({
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
            
            # Добавляем метаданные анализа
            metadata = analysis_data.get('analysis_metadata', {})
            if metadata:
                page_data["children"].append({
                    "object": "block",
                    "type": "divider"
                })
                
                page_data["children"].append({
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
            
            self.logger.info("✅ Данные для Notion созданы успешно")
            return page_data
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания данных для Notion: {e}")
            return {}
    
    def save_analysis_to_file(self, analysis_data: Dict[str, Any], output_path: str) -> bool:
        """
        Сохраняет результат анализа в файл
        
        Args:
            analysis_data: Результат анализа
            output_path: Путь для сохранения
            
        Returns:
            True если сохранение успешно
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"💾 Анализ сохранен в: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения анализа: {e}")
            return False
