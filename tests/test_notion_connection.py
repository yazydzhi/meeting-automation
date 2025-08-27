#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест соединения с Notion API и проверка базы данных
"""

import os
import requests
import json
from datetime import datetime

def test_notion_connection():
    """Тестирует соединение с Notion API"""
    
    print("🔍 ТЕСТ СОЕДИНЕНИЯ С NOTION")
    print("=" * 50)
    
    # Этап 1: Загрузка конфигурации
    print("\n📋 ЭТАП 1: Загрузка конфигурации...")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        notion_token = os.getenv('NOTION_TOKEN')
        database_id = os.getenv('NOTION_DATABASE_ID')
        
        if not notion_token:
            print("❌ NOTION_TOKEN не найден в .env")
            return False
            
        if not database_id:
            print("❌ NOTION_DATABASE_ID не найден в .env")
            return False
            
        print(f"✅ Токен: {'*' * 10}{notion_token[-4:] if notion_token else 'НЕТ'}")
        print(f"✅ База данных ID: {database_id}")
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False
    
    # Этап 2: Проверка токена
    print("\n🔑 ЭТАП 2: Проверка токена...")
    try:
        headers = {
            "Authorization": f"Bearer {notion_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        
        # Тестируем токен через простой запрос
        response = requests.get("https://api.notion.com/v1/users/me", headers=headers)
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"✅ Токен валиден")
            print(f"   Пользователь: {user_data.get('name', 'Неизвестно')}")
            print(f"   Email: {user_data.get('person', {}).get('email', 'Неизвестно')}")
        else:
            print(f"❌ Токен невалиден: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки токена: {e}")
        return False
    
    # Этап 3: Проверка базы данных
    print("\n📊 ЭТАП 3: Проверка базы данных...")
    try:
        response = requests.get(f"https://api.notion.com/v1/databases/{database_id}", headers=headers)
        
        if response.status_code == 200:
            db_data = response.json()
            print(f"✅ База данных найдена")
            print(f"   Название: {db_data.get('title', [{}])[0].get('text', {}).get('content', 'Без названия')}")
            
            # Безопасная обработка описания
            description = db_data.get('description', [])
            if description and len(description) > 0:
                desc_content = description[0].get('text', {}).get('content', 'Без описания')
                print(f"   Описание: {desc_content}")
            else:
                print(f"   Описание: Без описания")
            
            # Показываем свойства базы данных
            properties = db_data.get('properties', {})
            print(f"   Свойства: {list(properties.keys())}")
            
        else:
            print(f"❌ База данных не найдена: {response.status_code}")
            print(f"   Ответ: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка проверки базы данных: {e}")
        return False
    
    # Этап 4: Попытка создания тестовой страницы
    print("\n📝 ЭТАП 4: Тест создания страницы...")
    try:
        test_page_data = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"Тест соединения {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            }
                        }
                    ]
                }
            }
        }
        
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=test_page_data
        )
        
        if response.status_code == 200:
            page_data = response.json()
            page_id = page_data["id"]
            print(f"✅ Тестовая страница создана")
            print(f"   ID страницы: {page_id}")
            
            # Удаляем тестовую страницу
            print("   🗑️ Удаляю тестовую страницу...")
            delete_response = requests.delete(f"https://api.notion.com/v1/blocks/{page_id}", headers=headers)
            if delete_response.status_code == 200:
                print("   ✅ Тестовая страница удалена")
            else:
                print(f"   ⚠️ Не удалось удалить тестовую страницу: {delete_response.status_code}")
                
        else:
            print(f"❌ Не удалось создать тестовую страницу: {response.status_code}")
            print(f"   Ответ: {response.text}")
            print(f"   Отправленные данные: {json.dumps(test_page_data, indent=2, ensure_ascii=False)}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка создания тестовой страницы: {e}")
        return False
    
    # Этап 5: Проверка существующих страниц
    print("\n📚 ЭТАП 5: Проверка существующих страниц...")
    try:
        response = requests.post(
            f"https://api.notion.com/v1/databases/{database_id}/query",
            headers=headers,
            json={"page_size": 5}
        )
        
        if response.status_code == 200:
            query_data = response.json()
            pages = query_data.get('results', [])
            print(f"✅ Найдено страниц: {len(pages)}")
            
            for i, page in enumerate(pages[:3]):  # Показываем первые 3
                title = page.get('properties', {}).get('Name', {}).get('title', [{}])[0].get('text', {}).get('content', 'Без названия')
                created_time = page.get('created_time', 'Неизвестно')
                print(f"   {i+1}. {title} (создана: {created_time[:10]})")
                
        else:
            print(f"❌ Не удалось получить страницы: {response.status_code}")
            print(f"   Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка получения страниц: {e}")
    
    print("\n" + "=" * 50)
    print("✅ ТЕСТ ЗАВЕРШЕН УСПЕШНО!")
    return True

if __name__ == "__main__":
    test_notion_connection()
