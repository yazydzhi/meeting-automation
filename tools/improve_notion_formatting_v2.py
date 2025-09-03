#!/usr/bin/env python3
"""
Улучшенный скрипт для форматирования Notion страниц с правильным отображением
"""

import sqlite3
import requests
import os
import json
import re
from dotenv import load_dotenv

def load_config():
    """Загружает конфигурацию из .env"""
    load_dotenv()
    return {
        'notion_token': os.getenv('NOTION_TOKEN'),
        'db_path': 'data/system_state.db'
    }

def get_notion_headers(notion_token):
    """Возвращает заголовки для Notion API"""
    return {
        'Authorization': f'Bearer {notion_token}',
        'Notion-Version': '2022-06-28',
        'Content-Type': 'application/json'
    }

def clear_page_content(page_id, headers):
    """Очищает контент страницы (удаляет все блоки кроме заголовка)"""
    try:
        # Получаем все блоки
        blocks_url = f'https://api.notion.com/v1/blocks/{page_id}/children'
        response = requests.get(blocks_url, headers=headers)
        
        if response.status_code != 200:
            print(f"❌ Ошибка получения блоков: {response.status_code}")
            return False
        
        blocks_data = response.json()
        blocks = blocks_data.get('results', [])
        
        # Удаляем все блоки кроме первого (заголовок)
        for block in blocks[1:]:
            block_id = block['id']
            delete_url = f'https://api.notion.com/v1/blocks/{block_id}'
            delete_response = requests.delete(delete_url, headers=headers)
            
            if delete_response.status_code != 200:
                print(f"⚠️ Не удалось удалить блок {block_id}")
        
        print(f"✅ Контент страницы очищен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка очистки контента: {e}")
        return False

def parse_markdown_to_notion_blocks(markdown_text):
    """Парсит Markdown текст и преобразует в блоки Notion"""
    blocks = []
    lines = markdown_text.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if not line:
            i += 1
            continue
        
        # Заголовки
        if line.startswith('# '):
            blocks.append({
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line[2:]}}]
                }
            })
        elif line.startswith('## '):
            blocks.append({
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line[3:]}}]
                }
            })
        elif line.startswith('### '):
            blocks.append({
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line[4:]}}]
                }
            })
        
        # Списки
        elif line.startswith('- ') or line.startswith('* '):
            # Собираем все элементы списка
            list_items = []
            while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                item_text = lines[i].strip()[2:].strip()
                list_items.append(item_text)
                i += 1
            i -= 1  # Возвращаемся на одну строку назад
            
            # Добавляем элементы списка
            for item in list_items:
                blocks.append({
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": item}}]
                    }
                })
        
        elif re.match(r'^\d+\. ', line):
            # Собираем все элементы нумерованного списка
            list_items = []
            while i < len(lines) and re.match(r'^\d+\. ', lines[i].strip()):
                item_text = re.sub(r'^\d+\. ', '', lines[i].strip())
                list_items.append(item_text)
                i += 1
            i -= 1  # Возвращаемся на одну строку назад
            
            # Добавляем элементы списка
            for item in list_items:
                blocks.append({
                    "type": "numbered_list_item",
                    "numbered_list_item": {
                        "rich_text": [{"type": "text", "text": {"content": item}}]
                    }
                })
        
        # Разделители
        elif line.startswith('---') or line.startswith('***'):
            blocks.append({"type": "divider", "divider": {}})
        
        # Обычные параграфы
        else:
            # Собираем многострочный параграф
            paragraph_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(('#', '-', '*', '---', '***')) and not re.match(r'^\d+\. ', lines[i].strip()):
                paragraph_lines.append(lines[i].strip())
                i += 1
            i -= 1  # Возвращаемся на одну строку назад
            
            if paragraph_lines:
                paragraph_text = ' '.join(paragraph_lines)
                blocks.append({
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": paragraph_text}}]
                    }
                })
        
        i += 1
    
    return blocks

def format_rich_text_with_markdown(text):
    """Форматирует текст с поддержкой базового Markdown"""
    rich_text = []
    current_text = text
    current_formatting = {}
    
    # Обрабатываем жирный текст
    bold_pattern = r'\*\*(.*?)\*\*'
    italic_pattern = r'\*(.*?)\*'
    code_pattern = r'`(.*?)`'
    
    # Простая обработка - разбиваем по паттернам
    parts = re.split(r'(\*\*.*?\*\*|\*.*?\*|`.*?`)', current_text)
    
    for part in parts:
        if not part:
            continue
            
        if part.startswith('**') and part.endswith('**'):
            # Жирный текст
            content = part[2:-2]
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"bold": True}
            })
        elif part.startswith('*') and part.endswith('*') and not part.startswith('**'):
            # Курсив
            content = part[1:-1]
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"italic": True}
            })
        elif part.startswith('`') and part.endswith('`'):
            # Код
            content = part[1:-1]
            rich_text.append({
                "type": "text",
                "text": {"content": content},
                "annotations": {"code": True}
            })
        else:
            # Обычный текст
            rich_text.append({
                "type": "text",
                "text": {"content": part}
            })
    
    return rich_text

def create_structured_content_v2(event_data, transcript_content, summary_content, analysis_data):
    """Создает структурированный контент для Notion с улучшенным форматированием"""
    
    blocks = []
    
    # 1. Информация о встрече
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📋 Информация о встрече"}}]
            }
        },
        {
            "type": "callout",
            "callout": {
                "icon": {"emoji": "⏰"},
                "rich_text": format_rich_text_with_markdown(f"**Время:** {event_data.get('start_time', 'N/A')} - {event_data.get('end_time', 'N/A')}")
            }
        },
        {
            "type": "callout",
            "callout": {
                "icon": {"emoji": "👥"},
                "rich_text": format_rich_text_with_markdown(f"**Участники:** {event_data.get('attendees', 'N/A')}")
            }
        },
        {
            "type": "callout",
            "callout": {
                "icon": {"emoji": "🔗"},
                "rich_text": format_rich_text_with_markdown(f"**Ссылка на встречу:** {event_data.get('meeting_link', 'N/A')}")
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 2. Цели встречи
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🎯 Цели встречи"}}]
            }
        },
        {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": [{"type": "text", "text": {"content": "Добавить цели встречи..."}}]
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 3. Заметки
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📝 Заметки"}}]
            }
        },
        {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": "Здесь можно вести заметки во время встречи..."}}]
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 4. Действия
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "✅ Действия"}}]
            }
        },
        {
            "type": "to_do",
            "to_do": {
                "rich_text": [{"type": "text", "text": {"content": "Добавить действия..."}}],
                "checked": False
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 5. Ссылки
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "🔗 Ссылки"}}]
            }
        },
        {
            "type": "callout",
            "callout": {
                "icon": {"emoji": "📁"},
                "rich_text": format_rich_text_with_markdown(f"**Google Drive папка:** {event_data.get('drive_folder', 'N/A')}")
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 6. Следующие шаги
    blocks.extend([
        {
            "type": "heading_2",
            "heading_2": {
                "rich_text": [{"type": "text", "text": {"content": "📅 Следующие шаги"}}]
            }
        },
        {
            "type": "numbered_list_item",
            "numbered_list_item": {
                "rich_text": [{"type": "text", "text": {"content": "Запланировать следующие встречи..."}}]
            }
        },
        {"type": "divider", "divider": {}}
    ])
    
    # 7. Саммари и анализ
    if summary_content:
        blocks.extend([
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📊 Саммари и анализ"}}]
                }
            },
            {
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🤖"},
                    "rich_text": [{"type": "text", "text": {"content": "Сгенерировано автоматически системой анализа"}}]
                }
            }
        ])
        
        # Парсим саммари как Markdown
        summary_blocks = parse_markdown_to_notion_blocks(summary_content)
        blocks.extend(summary_blocks)
        
        # Добавляем детальный анализ если есть
        if analysis_data:
            blocks.extend([
                {
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "🔍 Детальный анализ"}}]
                    }
                }
            ])
            
            # Форматируем анализ
            if isinstance(analysis_data, dict):
                analysis_text = format_analysis_data_v2(analysis_data)
            else:
                analysis_text = str(analysis_data)
            
            # Парсим анализ как Markdown
            analysis_blocks = parse_markdown_to_notion_blocks(analysis_text)
            blocks.extend(analysis_blocks)
        
        blocks.append({"type": "divider", "divider": {}})
    
    # 8. Транскрипция
    if transcript_content:
        blocks.extend([
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "📝 Транскрипция встречи"}}]
                }
            },
            {
                "type": "callout",
                "callout": {
                    "icon": {"emoji": "🎤"},
                    "rich_text": [{"type": "text", "text": {"content": "Автоматически транскрибировано системой Whisper"}}]
                }
            }
        ])
        
        # Добавляем транскрипцию как обычный текст (разбиваем по частям)
        transcript_chunks = [transcript_content[i:i+1800] for i in range(0, len(transcript_content), 1800)]
        for chunk in transcript_chunks:
            blocks.append({
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": chunk}}]
                }
            })
    
    return blocks

def format_analysis_data_v2(analysis_data):
    """Форматирует данные анализа в читаемый Markdown текст"""
    if not isinstance(analysis_data, dict):
        return str(analysis_data)
    
    formatted_text = "## 🔍 Детальный анализ встречи\n\n"
    
    # Ключевые темы
    if 'key_topics' in analysis_data and analysis_data['key_topics']:
        formatted_text += "### Ключевые темы:\n"
        for topic in analysis_data['key_topics']:
            formatted_text += f"- {topic}\n"
        formatted_text += "\n"
    
    # Важные решения
    if 'decisions' in analysis_data and analysis_data['decisions']:
        formatted_text += "### Важные решения:\n"
        for decision in analysis_data['decisions']:
            formatted_text += f"- {decision}\n"
        formatted_text += "\n"
    
    # Следующие шаги
    if 'action_items' in analysis_data and analysis_data['action_items']:
        formatted_text += "### Следующие шаги:\n"
        for i, action in enumerate(analysis_data['action_items'], 1):
            formatted_text += f"{i}. {action}\n"
        formatted_text += "\n"
    
    # Участники
    if 'participants' in analysis_data and analysis_data['participants']:
        formatted_text += "### Участники и их роли:\n"
        for participant in analysis_data['participants']:
            formatted_text += f"- {participant}\n"
        formatted_text += "\n"
    
    # Общая оценка
    if 'summary' in analysis_data and analysis_data['summary']:
        formatted_text += f"### Общая оценка:\n{analysis_data['summary']}\n"
    
    return formatted_text

def improve_event_formatting_v2(event_id, config):
    """Улучшает форматирование для конкретного события с правильным Notion форматированием"""
    
    print(f"🎨 Улучшение форматирования для события: {event_id}")
    
    # Подключаемся к БД
    conn = sqlite3.connect(config['db_path'])
    cursor = conn.cursor()
    
    # Получаем данные события
    cursor.execute('''
        SELECT event_title, event_start_time, event_end_time, attendees, meeting_link, calendar_type
        FROM processed_events 
        WHERE event_id = ?
    ''', (event_id,))
    
    event_data = cursor.fetchone()
    if not event_data:
        print(f"❌ Событие {event_id} не найдено в БД")
        conn.close()
        return False
    
    title, start_time, end_time, attendees, meeting_link, calendar_type = event_data
    
    # Получаем Notion page_id
    cursor.execute('''
        SELECT page_id FROM notion_sync_status 
        WHERE event_id = ?
    ''', (event_id,))
    
    notion_result = cursor.fetchone()
    if not notion_result:
        print(f"❌ Notion страница для события {event_id} не найдена")
        conn.close()
        return False
    
    page_id = notion_result[0]
    
    # Получаем папку события
    cursor.execute('''
        SELECT folder_path FROM folder_creation_status 
        WHERE event_id = ?
    ''', (event_id,))
    
    folder_result = cursor.fetchone()
    if not folder_result:
        print(f"❌ Папка для события {event_id} не найдена")
        conn.close()
        return False
    
    folder_path = folder_result[0]
    
    # Получаем контент файлов
    transcript_content = ""
    summary_content = ""
    analysis_data = None
    
    # Транскрипция
    transcript_file = os.path.join(folder_path, f"{os.path.basename(folder_path)}___transcript.txt")
    if os.path.exists(transcript_file):
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            print(f"✅ Транскрипция загружена: {len(transcript_content)} символов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки транскрипции: {e}")
    
    # Саммари
    summary_file = os.path.join(folder_path, f"{os.path.basename(folder_path)}___transcript_summary.txt")
    if os.path.exists(summary_file):
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_content = f.read()
            print(f"✅ Саммари загружено: {len(summary_content)} символов")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки саммари: {e}")
    
    # Анализ
    analysis_file = os.path.join(folder_path, f"{os.path.basename(folder_path)}___transcript_analysis.json")
    if os.path.exists(analysis_file):
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                analysis_data = json.load(f)
            print(f"✅ Анализ загружен")
        except Exception as e:
            print(f"⚠️ Ошибка загрузки анализа: {e}")
    
    conn.close()
    
    # Подготавливаем данные для форматирования
    event_data_dict = {
        'title': title,
        'start_time': start_time,
        'end_time': end_time,
        'attendees': attendees,
        'meeting_link': meeting_link,
        'drive_folder': f"https://drive.google.com/drive/folders/{os.path.basename(folder_path)}"
    }
    
    # Создаем структурированный контент
    blocks = create_structured_content_v2(event_data_dict, transcript_content, summary_content, analysis_data)
    
    # Очищаем страницу и добавляем новый контент
    headers = get_notion_headers(config['notion_token'])
    
    print(f"🧹 Очистка контента страницы...")
    if not clear_page_content(page_id, headers):
        return False
    
    print(f"📝 Добавление структурированного контента...")
    
    # Добавляем блоки по частям (лимит Notion API)
    chunk_size = 50  # Максимум блоков за один запрос
    for i in range(0, len(blocks), chunk_size):
        chunk = blocks[i:i+chunk_size]
        
        blocks_url = f'https://api.notion.com/v1/blocks/{page_id}/children'
        blocks_data = {'children': chunk}
        
        response = requests.patch(blocks_url, headers=headers, json=blocks_data)
        
        if response.status_code == 200:
            print(f"✅ Добавлено {len(chunk)} блоков")
        else:
            print(f"❌ Ошибка добавления блоков: {response.status_code}")
            print(f"Ответ: {response.text}")
            return False
    
    print(f"🎉 Форматирование завершено успешно!")
    return True

def main():
    """Основная функция"""
    config = load_config()
    
    if not config['notion_token']:
        print("❌ NOTION_TOKEN не найден в переменных окружения")
        return
    
    # Улучшаем форматирование для события "ПСБ //SmartDeal - эквайринг"
    event_id = 'ical_2025-08-29_84286d0f'
    
    success = improve_event_formatting_v2(event_id, config)
    
    if success:
        print(f"\n🎯 Форматирование события '{event_id}' завершено успешно!")
        print(f"📄 Проверьте Notion страницу для просмотра улучшенного форматирования")
    else:
        print(f"\n❌ Ошибка при форматировании события '{event_id}'")

if __name__ == "__main__":
    main()
