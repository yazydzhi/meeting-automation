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
        # Извлекаем только поле children из шаблона
        if "children" in template:
            template_data = {"children": template["children"]}
        else:
            print(f"⚠️ В шаблоне отсутствует поле 'children'")
            return False
            
        response = requests.patch(url, headers=headers, json=template_data)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"✖ Ошибка применения шаблона к странице {page_id}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Тело ответа: {e.response.text}")
            print(f"   Статус: {e.response.status_code}")
        return False


def add_meeting_details_to_page(
    notion_token: str,
    page_id: str,
    event_data: Dict[str, Any],
    logger=None
) -> bool:
    """
    Добавляет детальную информацию о встрече на страницу Notion.
    
    Args:
        notion_token: Токен для API Notion
        page_id: ID страницы для обновления
        event_data: Данные события
        logger: Логгер (опционально)
        
    Returns:
        True если информация успешно добавлена, False в противном случае
    """
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Формируем блоки с детальной информацией
    detail_blocks = []
    
    # Добавляем описание встречи, если есть
    if event_data.get("description"):
        detail_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📋 Описание: {event_data.get('description', '')}"
                        }
                    }
                ]
            }
        })
    
    # Добавляем местоположение, если есть
    if event_data.get("location"):
        detail_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📍 Местоположение: {event_data.get('location', '')}"
                        }
                    }
                ]
            }
        })
    
    # Добавляем участников, если есть
    if event_data.get("attendees") and len(event_data.get("attendees", [])) > 0:
        attendees_text = ", ".join(event_data.get("attendees", [])[:10])
        detail_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"👥 Участники: {attendees_text}"
                        }
                    }
                ]
            }
        })
    
    # Добавляем ссылку на встречу, если есть
    if event_data.get("meeting_link"):
        detail_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": "🔗 Ссылка на встречу: "
                        }
                    },
                    {
                        "type": "text",
                        "text": {
                            "content": event_data.get("meeting_link", ""),
                            "link": {
                                "url": event_data.get("meeting_link", "")
                            }
                        }
                    }
                ]
            }
        })
    
    # Добавляем источник календаря
    if event_data.get("calendar_source"):
        detail_blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": f"📅 Источник: {event_data.get('calendar_source', '')}"
                        }
                    }
                ]
            }
        })
    
    # Если есть детали для добавления
    if detail_blocks:
        try:
            url = f"https://api.notion.com/v1/blocks/{page_id}/children"
            response = requests.patch(url, headers=headers, json={"children": detail_blocks})
            response.raise_for_status()
            
            if logger:
                logger.info(f"✅ Детальная информация о встрече добавлена на страницу {page_id}")
            else:
                print(f"✅ Детальная информация о встрече добавлена на страницу {page_id}")
            
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"❌ Ошибка добавления деталей встречи на страницу {page_id}: {e}")
            else:
                print(f"❌ Ошибка добавления деталей встречи на страницу {page_id}: {e}")
            return False
    
    return True  # Если нечего добавлять, считаем успешным


def create_simple_notion_page(
    notion_token: str,
    database_id: str,
    event_data: Dict[str, Any],
    logger=None
) -> str:
    """
    Создает простую страницу в базе данных Notion без шаблона.
    
    Args:
        notion_token: Токен для API Notion
        database_id: ID базы данных
        event_data: Данные события
        
    Returns:
        ID созданной страницы или пустая строка в случае ошибки
    """
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Создаем свойства страницы
    notion_properties = {
        "Name": {
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": event_data.get("title", "Встреча без названия")
                    }
                }
            ]
        }
    }
    
    # Добавляем дату и время, если есть
    if event_data.get("date") and event_data.get("start_time"):
        # Формируем полную дату-время в формате ISO
        date_str = event_data.get("date", "")
        start_time = event_data.get("start_time", "")
        end_time = event_data.get("end_time", "")
        
        # Создаем объект даты с временем
        # Время уже конвертировано в локальную таймзону, не добавляем +03:00
        date_obj = {
            "start": f"{date_str}T{start_time}:00"  # Без таймзоны, Notion использует локальную
        }
        
        # Добавляем время окончания, если есть
        if end_time:
            date_obj["end"] = f"{date_str}T{end_time}:00"
        
        notion_properties["Date"] = {"date": date_obj}
        
        if logger:
            logger.info(f"🕐 Создаю событие в Notion: {date_str} {start_time}-{end_time}")
    elif event_data.get("date"):
        # Если есть только дата без времени
        notion_properties["Date"] = {
            "date": {
                "start": event_data.get("date", "")
            }
        }
    
    # Добавляем участников, если есть
    if event_data.get("attendees"):
        attendees_list = event_data.get("attendees", [])
        if isinstance(attendees_list, list) and attendees_list:
            # Объединяем всех участников в одну строку
            attendees_text = ", ".join(attendees_list[:10])  # Ограничиваем количество
            notion_properties["Attendees"] = {
                "rich_text": [
                    {
                        "type": "text",
                        "text": {
                            "content": attendees_text
                        }
                    }
                ]
            }
    
    # Добавляем ссылку на встречу, если есть
    if event_data.get("meeting_link"):
        notion_properties["Meeting Link"] = {
            "url": event_data.get("meeting_link", "")
        }
    
    # Добавляем тип календаря
    if event_data.get("account_type"):
        notion_properties["Calendar"] = {
            "select": {
                "name": event_data.get("account_type", "unknown")
            }
        }
    
    # Добавляем полный путь к папке Drive, если есть
    if event_data.get("folder_link"):
        notion_properties["Drive Folder"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": event_data.get("folder_link", "")
                    }
                }
            ]
        }
    
    # Добавляем Event ID, если есть
    if event_data.get("event_id"):
        notion_properties["Event ID"] = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": str(event_data.get("event_id", ""))
                    }
                }
            ]
        }
    
    create_data = {
        "parent": {"database_id": database_id},
        "properties": notion_properties
    }
    
    try:
        if logger:
            logger.info(f"🔧 Создаю простую страницу в Notion...")
            logger.info(f"   База данных: {database_id}")
            logger.info(f"   Название: {event_data.get('title', 'Встреча без названия')}")
            logger.info(f"   Свойства: {list(notion_properties.keys())}")
        else:
            print(f"🔧 Создаю простую страницу в Notion...")
            print(f"   База данных: {database_id}")
            print(f"   Название: {event_data.get('title', 'Встреча без названия')}")
            print(f"   Свойства: {list(notion_properties.keys())}")
        
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=create_data
        )
        
        if response.status_code != 200:
            if logger:
                logger.error(f"✖ Ошибка создания простой страницы: {response.status_code}")
                logger.error(f"   Тело ответа: {response.text}")
            else:
                print(f"✖ Ошибка создания простой страницы: {response.status_code}")
                print(f"   Тело ответа: {response.text}")
            return ""
            
        response.raise_for_status()
        page_data = response.json()
        page_id = page_data["id"]
        
        if logger:
            logger.info(f"✅ Простая страница создана успешно: {page_id}")
        else:
            print(f"✅ Простая страница создана успешно: {page_id}")
        return page_id
        
    except Exception as e:
        if logger:
            logger.error(f"✖ Исключение при создании простой страницы: {e}")
        else:
            print(f"✖ Исключение при создании простой страницы: {e}")
        return ""


def check_page_exists(
    notion_token: str,
    database_id: str,
    event_title: str,
    event_date: str,
    logger=None
) -> str:
    """
    Проверяет, существует ли уже страница для события с таким названием и датой.
    
    Args:
        notion_token: Токен для API Notion
        database_id: ID базы данных
        event_title: Название события
        event_date: Дата события
        
    Returns:
        ID существующей страницы или пустая строка, если страница не найдена
    """
    import requests
    
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    # Ищем страницы с таким названием и датой
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    query_data = {
        "filter": {
            "and": [
                {
                    "property": "Name",
                    "title": {
                        "equals": event_title
                    }
                },
                {
                    "property": "Date",
                    "date": {
                        "equals": event_date
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=query_data)
        response.raise_for_status()
        
        results = response.json().get("results", [])
        
        if results:
            existing_page_id = results[0]["id"]
            if logger:
                logger.info(f"🔍 Найдена существующая страница: {existing_page_id}")
            else:
                print(f"🔍 Найдена существующая страница: {existing_page_id}")
            return existing_page_id
        
        return ""
        
    except Exception as e:
        if logger:
            logger.error(f"✖ Ошибка проверки существования страницы: {e}")
        else:
            print(f"✖ Ошибка проверки существования страницы: {e}")
        return ""


def create_page_with_template(
    notion_token: str,
    database_id: str,
    event_data: Dict[str, Any],
    template: Dict[str, Any],
    logger=None
) -> str:
    """
    Создает новую страницу в базе данных с применением шаблона.
    
    Args:
        notion_token: Токен для API Notion
        database_id: ID базы данных
        event_data: Данные события
        template: Шаблон для применения
        
    Returns:
        ID созданной страницы или пустая строка в случае ошибки
    """
    # Сначала проверяем, существует ли уже страница для этого события
    existing_page_id = check_page_exists(
        notion_token, 
        database_id, 
        event_data.get("title", ""), 
        event_data.get("date", ""),
        logger
    )
    
    if existing_page_id:
        if logger:
            logger.info(f"⏭️ Страница уже существует, пропускаю создание: {existing_page_id}")
        else:
            print(f"⏭️ Страница уже существует, пропускаю создание: {existing_page_id}")
        
        # Добавляем детальную информацию на существующую страницу
        if logger:
            logger.info(f"🔧 Добавляю детальную информацию на существующую страницу {existing_page_id}...")
        else:
            print(f"🔧 Добавляю детальную информацию на существующую страницу {existing_page_id}...")
        
        add_meeting_details_to_page(notion_token, existing_page_id, event_data, logger)
        
        return existing_page_id
    
    # Сначала попробуем создать простую страницу
    page_id = create_simple_notion_page(notion_token, database_id, event_data, logger)
    if not page_id:
        return ""
    
    # Теперь попробуем применить шаблон
    if logger:
        logger.info(f"🔧 Применяю шаблон к странице {page_id}...")
    else:
        print(f"🔧 Применяю шаблон к странице {page_id}...")
        
    if apply_template_to_page(notion_token, page_id, template):
        if logger:
            logger.info(f"✅ Шаблон применен успешно")
        else:
            print(f"✅ Шаблон применен успешно")
        
        # Добавляем детальную информацию о встрече
        if logger:
            logger.info(f"🔧 Добавляю детальную информацию о встрече на страницу {page_id}...")
        else:
            print(f"🔧 Добавляю детальную информацию о встрече на страницу {page_id}...")
        
        add_meeting_details_to_page(notion_token, page_id, event_data, logger)
        
        return page_id
    else:
        if logger:
            logger.warning(f"⚠️ Страница создана, но шаблон не применен: {page_id}")
        else:
            print(f"⚠️ Страница создана, но шаблон не применен: {page_id}")
        return page_id
