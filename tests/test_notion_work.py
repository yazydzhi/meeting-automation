#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест Notion API для рабочего аккаунта
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Загружаем конфигурацию рабочего аккаунта
load_dotenv('env.work')

def test_notion_connection():
    """Тестируем подключение к Notion."""
    print("🔍 Тестирование подключения к Notion...")
    
    # Получаем данные из конфигурации
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    print(f"📋 Токен: {notion_token[:20]}..." if notion_token else "❌ Токен не найден")
    print(f"📊 ID базы данных: {database_id}")
    
    if not notion_token or not database_id:
        print("❌ Отсутствуют необходимые данные для Notion")
        return False
    
    # Настраиваем заголовки
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Тест 1: Получаем информацию о базе данных
    print("\n📊 Тест 1: Получение информации о базе данных...")
    try:
        response = requests.get(
            f'https://api.notion.com/v1/databases/{database_id}',
            headers=headers
        )
        
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            db_info = response.json()
            print(f"✅ База данных найдена: {db_info.get('title', [{}])[0].get('plain_text', 'Без названия')}")
            
            # Показываем свойства базы данных
            properties = db_info.get('properties', {})
            print(f"📋 Свойства базы данных:")
            for prop_name, prop_info in properties.items():
                prop_type = prop_info.get('type', 'unknown')
                print(f"   - {prop_name}: {prop_type}")
            
            return True
        else:
            print(f"❌ Ошибка получения базы данных: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False
    
    return False

def test_notion_query():
    """Тестируем запрос к базе данных Notion."""
    print("\n🔍 Тест 2: Запрос к базе данных...")
    
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("❌ Отсутствуют необходимые данные для Notion")
        return False
    
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Простой запрос без фильтров
    query_data = {}
    
    try:
        response = requests.post(
            f'https://api.notion.com/v1/databases/{database_id}/query',
            headers=headers,
            json=query_data
        )
        
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Найдено записей: {len(results)}")
            
            if results:
                print(f"📋 Первая запись:")
                first_result = results[0]
                properties = first_result.get('properties', {})
                
                for prop_name, prop_info in properties.items():
                    prop_type = prop_info.get('type', 'unknown')
                    print(f"   - {prop_name} ({prop_type}): {prop_info}")
            
            return True
        else:
            print(f"❌ Ошибка запроса: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def test_notion_calendar_query():
    """Тестируем запрос календаря к Notion."""
    print("\n📅 Тест 3: Запрос календаря...")
    
    notion_token = os.getenv('NOTION_TOKEN')
    database_id = os.getenv('NOTION_DATABASE_ID')
    
    if not notion_token or not database_id:
        print("❌ Отсутствуют необходимые данные для Notion")
        return False
    
    headers = {
        'Authorization': f'Bearer {notion_token}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'
    }
    
    # Запрос с фильтром по дате (как в calendar_alternatives.py)
    query_data = {
        "filter": {
            "and": [
                {
                    "property": "Дата",
                    "date": {
                        "on_or_after": "2025-08-22"
                    }
                },
                {
                    "property": "Дата",
                    "date": {
                        "on_or_before": "2025-08-29"
                    }
                }
            ]
        }
    }
    
    try:
        response = requests.post(
            f'https://api.notion.com/v1/databases/{database_id}/query',
            headers=headers,
            json=query_data
        )
        
        print(f"📡 Статус: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"✅ Найдено событий: {len(results)}")
            
            if results:
                print(f"📋 Первое событие:")
                first_result = results[0]
                properties = first_result.get('properties', {})
                
                for prop_name, prop_info in properties.items():
                    prop_type = prop_info.get('type', 'unknown')
                    print(f"   - {prop_name} ({prop_type}): {prop_info}")
            
            return True
        else:
            print(f"❌ Ошибка запроса календаря: {response.status_code}")
            print(f"📄 Ответ: {response.text}")
            
            # Пробуем понять, в чем проблема
            if response.status_code == 400:
                print("🔍 Возможные причины ошибки 400:")
                print("   - Неправильная структура фильтра")
                print("   - Свойство 'Дата' не существует")
                print("   - Неправильный формат даты")
            
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return False

def main():
    """Основная функция."""
    print("🚀 Тест Notion API для рабочего аккаунта")
    print("=" * 50)
    
    # Тест 1: Подключение
    if test_notion_connection():
        print("\n✅ Подключение к Notion успешно")
        
        # Тест 2: Простой запрос
        if test_notion_query():
            print("\n✅ Простой запрос успешен")
            
            # Тест 3: Запрос календаря
            if test_notion_calendar_query():
                print("\n✅ Запрос календаря успешен")
            else:
                print("\n❌ Запрос календаря не удался")
        else:
            print("\n❌ Простой запрос не удался")
    else:
        print("\n❌ Подключение к Notion не удалось")
    
    print("\n🏁 Тестирование завершено")

if __name__ == "__main__":
    main()
