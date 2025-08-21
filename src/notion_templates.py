"""
Модуль для работы с шаблонами страниц Notion.
Содержит функции для загрузки и применения шаблонов к страницам встреч.
"""

import json
import os
from typing import Dict, Any, List
from datetime import datetime


def load_meeting_template(template_path: str = "templates/meeting_page_template.json") -> Dict[str, Any]:
    """
    Загружает шаблон страницы встречи из JSON файла.
    
    Args:
        template_path: Путь к файлу шаблона
        
    Returns:
        Словарь с шаблоном страницы
        
    Raises:
        FileNotFoundError: Если файл шаблона не найден
        json.JSONDecodeError: Если файл содержит неверный JSON
    """
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = json.load(f)
        return template
    except FileNotFoundError:
        raise FileNotFoundError(f"Шаблон не найден: {template_path}")
    except json.JSONDecodeError as e:
        raise json.JSONDecodeError(f"Ошибка парсинга JSON в шаблоне: {e}", e.doc, e.pos)


def create_customized_template(
    title: str,
    start_time: str,
    end_time: str,
    attendees: List[str],
    meeting_link: str = "",
    drive_link: str = ""
) -> Dict[str, Any]:
    """
    Создает кастомизированный шаблон на основе базового шаблона.
    
    Args:
        title: Название встречи
        start_time: Время начала встречи
        end_time: Время окончания встречи
        attendees: Список участников
        meeting_link: Ссылка на встречу
        drive_link: Ссылка на папку Google Drive
        
    Returns:
        Кастомизированный шаблон страницы
    """
    # Загружаем базовый шаблон
    base_template = load_meeting_template()
    
    # Создаем кастомизированную версию
    customized_template = {
        "children": []
    }
    
    # Добавляем заголовок с названием встречи
    customized_template["children"].append({
        "object": "block",
        "type": "heading_1",
        "heading_1": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": f"📋 {title}"
                    }
                }
            ]
        }
    })
    
    # Добавляем информацию о времени
    if start_time and end_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            time_info = f"⏰ {start_dt.strftime('%d.%m.%Y %H:%M')} - {end_dt.strftime('%H:%M')}"
            
            customized_template["children"].append({
                "object": "block",
                "type": "callout",
                "callout": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": time_info
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
        except Exception:
            # Если не удалось распарсить время, используем оригинальный блок
            pass
    
    # Добавляем участников
    if attendees:
        attendees_text = ", ".join(attendees)
        customized_template["children"].append({
            "object": "block",
            "type": "callout",
            "callout": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"👥 Участники: {attendees_text}"
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
    
    # Добавляем разделитель
    customized_template["children"].append({
        "object": "block",
        "type": "divider",
        "divider": {}
    })
    
    # Добавляем остальные блоки из базового шаблона
    for block in base_template["children"]:
        # Пропускаем заголовок и время, так как мы их уже добавили
        if block.get("type") in ["heading_1"]:
            continue
        if (block.get("type") == "callout" and 
            block.get("callout", {}).get("rich_text", [{}])[0].get("text", {}).get("content", "").startswith("Время встречи")):
            continue
            
        customized_template["children"].append(block)
    
    # Добавляем ссылки в конец
    if meeting_link or drive_link:
        customized_template["children"].append({
            "object": "block",
            "type": "divider",
            "divider": {}
        })
        
        customized_template["children"].append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🔗 Полезные ссылки"
                        }
                    }
                ]
            }
        })
        
        if meeting_link:
            customized_template["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📹 "
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": "Ссылка на встречу",
                                "link": {
                                    "url": meeting_link
                                }
                            }
                        }
                    ]
                }
            })
        
        if drive_link:
            customized_template["children"].append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "📁 "
                            }
                        },
                        {
                            "type": "text",
                            "text": {
                                "content": "Папка Google Drive",
                                "link": {
                                    "url": drive_link
                                }
                            }
                        }
                    ]
                }
            })
    
    return customized_template


def apply_template_to_page(
    notion_token: str,
    page_id: str,
    template: Dict[str, Any]
) -> bool:
    """
    Применяет шаблон к существующей странице Notion.
    
    Args:
        notion_token: Токен для API Notion
        page_id: ID страницы для обновления
        template: Шаблон для применения
        
    Returns:
        True если шаблон успешно применен, False в противном случае
    """
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Добавляем блоки шаблона к странице
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    try:
        response = requests.patch(url, headers=headers, json=template)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"✖ Ошибка применения шаблона к странице {page_id}: {e}")
        return False


def create_page_with_template(
    notion_token: str,
    database_id: str,
    properties: Dict[str, Any],
    template: Dict[str, Any]
) -> str:
    """
    Создает новую страницу в базе данных с применением шаблона.
    
    Args:
        notion_token: Токен для API Notion
        database_id: ID базы данных
        properties: Свойства страницы
        template: Шаблон для применения
        
    Returns:
        ID созданной страницы или пустая строка в случае ошибки
    """
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Сначала создаем страницу с базовыми свойствами
    create_data = {
        "parent": {"database_id": database_id},
        "properties": properties
    }
    
    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=create_data
        )
        response.raise_for_status()
        page_data = response.json()
        page_id = page_data["id"]
        
        # Теперь применяем шаблон к созданной странице
        if apply_template_to_page(notion_token, page_id, template):
            return page_id
        else:
            print(f"⚠️ Страница создана, но шаблон не применен: {page_id}")
            return page_id
            
    except Exception as e:
        print(f"✖ Ошибка создания страницы с шаблоном: {e}")
        return ""
