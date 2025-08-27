#!/usr/bin/env python3
"""
Скрипт для проверки и обновления всех существующих страниц в Notion
с детальной информацией о встречах.
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, Any, List

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from config_manager import ConfigManager
    from notion_templates import add_meeting_details_to_page
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


def get_all_notion_pages(notion_token: str, database_id: str) -> List[Dict[str, Any]]:
    """
    Получает все страницы из базы данных Notion.
    
    Args:
        notion_token: Токен для API Notion
        database_id: ID базы данных
        
    Returns:
        Список страниц с их данными
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    all_pages = []
    has_more = True
    start_cursor = None
    
    while has_more:
        query_data = {
            "page_size": 100,
            "sorts": [
                {
                    "property": "Date",
                    "direction": "descending"
                }
            ]
        }
        
        if start_cursor:
            query_data["start_cursor"] = start_cursor
        
        try:
            response = requests.post(url, headers=headers, json=query_data)
            response.raise_for_status()
            
            data = response.json()
            pages = data.get("results", [])
            all_pages.extend(pages)
            
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")
            
            print(f"📄 Загружено {len(pages)} страниц...")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки страниц: {e}")
            break
    
    return all_pages


def extract_page_data(page: Dict[str, Any]) -> Dict[str, Any]:
    """
    Извлекает данные страницы для анализа.
    
    Args:
        page: Данные страницы из Notion API
        
    Returns:
        Словарь с извлеченными данными
    """
    properties = page.get("properties", {})
    
    # Извлекаем название
    title_prop = properties.get("Name", {})
    title = ""
    if title_prop.get("title"):
        title = title_prop["title"][0].get("text", {}).get("content", "")
    
    # Извлекаем дату
    date_prop = properties.get("Date", {}).get("date", {})
    date = date_prop.get("start", "") if date_prop else ""
    
    # Извлекаем Event ID
    event_id_prop = properties.get("Event ID", {})
    event_id = ""
    if event_id_prop.get("rich_text"):
        event_id = event_id_prop["rich_text"][0].get("text", {}).get("content", "")
    
    # Извлекаем тип календаря
    calendar_prop = properties.get("Calendar", {})
    calendar_type = ""
    if calendar_prop.get("select"):
        calendar_type = calendar_prop["select"].get("name", "")
    
    # Извлекаем участников
    attendees_prop = properties.get("Attendees", {})
    attendees = []
    if attendees_prop.get("rich_text"):
        attendees_text = attendees_prop["rich_text"][0].get("text", {}).get("content", "")
        if attendees_text:
            attendees = [email.strip() for email in attendees_text.split(",")]
    
    # Извлекаем ссылку на встречу
    meeting_link_prop = properties.get("Meeting Link", {})
    meeting_link = meeting_link_prop.get("url", "") if meeting_link_prop else ""
    
    # Извлекаем Drive Folder
    drive_folder_prop = properties.get("Drive Folder", {})
    drive_folder = ""
    if drive_folder_prop.get("rich_text"):
        drive_folder = drive_folder_prop["rich_text"][0].get("text", {}).get("content", "")
    
    return {
        "page_id": page.get("id", ""),
        "title": title,
        "date": date,
        "event_id": event_id,
        "calendar_type": calendar_type,
        "attendees": attendees,
        "meeting_link": meeting_link,
        "drive_folder": drive_folder,
        "url": page.get("url", "")
    }


def check_page_content(notion_token: str, page_id: str) -> Dict[str, Any]:
    """
    Проверяет содержимое страницы Notion.
    
    Args:
        notion_token: Токен для API Notion
        page_id: ID страницы
        
    Returns:
        Словарь с информацией о содержимом страницы
    """
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        blocks = data.get("results", [])
        
        # Анализируем содержимое
        has_description = False
        has_location = False
        has_attendees = False
        has_meeting_link = False
        has_calendar_source = False
        
        for block in blocks:
            if block.get("type") == "paragraph":
                rich_text = block.get("paragraph", {}).get("rich_text", [])
                if rich_text:
                    content = rich_text[0].get("text", {}).get("content", "")
                    if "📋 Описание:" in content:
                        has_description = True
                    elif "📍 Местоположение:" in content:
                        has_location = True
                    elif "👥 Участники:" in content:
                        has_attendees = True
                    elif "🔗 Ссылка на встречу:" in content:
                        has_meeting_link = True
                    elif "📅 Источник:" in content:
                        has_calendar_source = True
        
        return {
            "has_description": has_description,
            "has_location": has_location,
            "has_attendees": has_attendees,
            "has_meeting_link": has_meeting_link,
            "has_calendar_source": has_calendar_source,
            "total_blocks": len(blocks)
        }
        
    except Exception as e:
        print(f"❌ Ошибка проверки содержимого страницы {page_id}: {e}")
        return {}


def update_page_with_details(notion_token: str, page_data: Dict[str, Any], content_info: Dict[str, Any]) -> bool:
    """
    Обновляет страницу детальной информацией, если её не хватает.
    
    Args:
        notion_token: Токен для API Notion
        page_data: Данные страницы
        content_info: Информация о содержимом
        
    Returns:
        True если страница обновлена, False в противном случае
    """
    # Проверяем, что нужно добавить
    needs_update = False
    
    if not content_info.get("has_description") and page_data.get("title"):
        needs_update = True
    
    if not content_info.get("has_location"):
        needs_update = True
    
    if not content_info.get("has_attendees") and page_data.get("attendees"):
        needs_update = True
    
    if not content_info.get("has_meeting_link") and page_data.get("meeting_link"):
        needs_update = True
    
    if not content_info.get("has_calendar_source") and page_data.get("calendar_type"):
        needs_update = True
    
    if not needs_update:
        return False
    
    # Формируем данные для обновления
    event_data = {
        "title": page_data.get("title", ""),
        "description": "",  # Будем добавлять базовое описание
        "location": "",     # Будем добавлять базовое местоположение
        "attendees": page_data.get("attendees", []),
        "meeting_link": page_data.get("meeting_link", ""),
        "calendar_source": page_data.get("calendar_type", ""),
        "event_id": page_data.get("event_id", ""),
        "folder_link": page_data.get("drive_folder", "")
    }
    
    # Добавляем базовое описание, если его нет
    if not content_info.get("has_description"):
        event_data["description"] = f"Встреча: {page_data.get('title', '')}"
    
    # Добавляем базовое местоположение, если его нет
    if not content_info.get("has_location"):
        event_data["location"] = "Онлайн" if page_data.get("meeting_link") else "Не указано"
    
    # Обновляем страницу
    try:
        success = add_meeting_details_to_page(
            notion_token,
            page_data["page_id"],
            event_data,
            None  # Без логгера для этого скрипта
        )
        
        if success:
            print(f"✅ Страница обновлена: {page_data['title']}")
            return True
        else:
            print(f"❌ Ошибка обновления страницы: {page_data['title']}")
            return False
            
    except Exception as e:
        print(f"❌ Исключение при обновлении страницы {page_data['title']}: {e}")
        return False


def main():
    """Основная функция скрипта."""
    print("🔍 Скрипт проверки и обновления страниц Notion")
    print("=" * 50)
    
    # Загружаем конфигурацию
    try:
        config_manager = ConfigManager()
        notion_config = config_manager.get_notion_config()
        notion_token = notion_config.get('token')
        database_id = notion_config.get('database_id')
        
        if not notion_token or not database_id:
            print("❌ Не настроены Notion токен или ID базы данных")
            return
        
        print(f"✅ Конфигурация загружена")
        print(f"   База данных: {database_id}")
        print(f"   Токен: {'*' * 10 + notion_token[-4:] if notion_token else 'НЕТ'}")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return
    
    # Получаем все страницы
    print("\n📄 Загружаю все страницы из базы данных...")
    pages = get_all_notion_pages(notion_token, database_id)
    
    if not pages:
        print("❌ Не удалось загрузить страницы")
        return
    
    print(f"✅ Загружено {len(pages)} страниц")
    
    # Анализируем каждую страницу
    print("\n🔍 Анализирую содержимое страниц...")
    
    updated_count = 0
    total_pages = len(pages)
    
    for i, page in enumerate(pages, 1):
        print(f"\n📄 Страница {i}/{total_pages}: {page.get('id', '')}")
        
        # Извлекаем данные страницы
        page_data = extract_page_data(page)
        
        if not page_data.get("title"):
            print("   ⏭️ Пропускаю страницу без названия")
            continue
        
        print(f"   📋 Название: {page_data['title']}")
        print(f"   📅 Дата: {page_data['date']}")
        print(f"   🆔 Event ID: {page_data['event_id']}")
        print(f"   📱 Ссылка: {page_data['url']}")
        
        # Проверяем содержимое
        content_info = check_page_content(notion_token, page_data["page_id"])
        
        if content_info:
            print(f"   📊 Блоков: {content_info.get('total_blocks', 0)}")
            print(f"   📋 Описание: {'✅' if content_info.get('has_description') else '❌'}")
            print(f"   📍 Местоположение: {'✅' if content_info.get('has_location') else '❌'}")
            print(f"   👥 Участники: {'✅' if content_info.get('has_attendees') else '❌'}")
            print(f"   🔗 Ссылка: {'✅' if content_info.get('has_meeting_link') else '❌'}")
            print(f"   📅 Источник: {'✅' if content_info.get('has_calendar_source') else '❌'}")
        
        # Обновляем страницу, если нужно
        if update_page_with_details(notion_token, page_data, content_info):
            updated_count += 1
        
        # Небольшая пауза между запросами
        import time
        time.sleep(0.5)
    
    # Итоговая статистика
    print("\n" + "=" * 50)
    print("📊 ИТОГОВАЯ СТАТИСТИКА")
    print(f"   Всего страниц: {total_pages}")
    print(f"   Обновлено: {updated_count}")
    print(f"   Не требовали обновления: {total_pages - updated_count}")
    
    if updated_count > 0:
        print(f"\n✅ Успешно обновлено {updated_count} страниц!")
    else:
        print(f"\n⏭️ Все страницы уже содержат необходимую информацию")


if __name__ == "__main__":
    main()
