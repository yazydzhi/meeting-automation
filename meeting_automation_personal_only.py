#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meeting_automation_personal_only.py
----------------------------------
Версия meeting_automation.py только для личного аккаунта
Включает полную функциональность: Calendar + Drive + Notion
"""

import os
import sys
import json
import time
import argparse
import datetime as dt
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

from dotenv import load_dotenv
import requests

# Google APIs
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Local modules
try:
    from src.notion_templates import create_customized_template, create_page_with_template
except ImportError:
    # Fallback if module not found
    create_customized_template = None
    create_page_with_template = None

# ---------------------------------------------------------------------------
# Path expansion helper
# ---------------------------------------------------------------------------
def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p)).expanduser()

# ---------------------------------------------------------------------------
# Константы и вспомогательные утилиты
# ---------------------------------------------------------------------------

# Scopes для личного аккаунта (Calendar + Drive)
SCOPES_PERSONAL = [
    "https://www.googleapis.com/auth/calendar.readonly",  # Calendar
    "https://www.googleapis.com/auth/drive",              # Drive (полный доступ)
    "https://www.googleapis.com/auth/drive.file",         # Drive (файлы приложения)
]

ISO_FMT = "%Y-%m-%dT%H:%M:%S%z"

# Проперти в Notion (ожидаемая схема БД)
NOTION_PROP = {
    "title": "Name",              # Title property
    "date": "Date",              # Date property
    "calendar": "Calendar",      # Select: Personal
    "attendees": "Attendees",    # Rich text
    "meeting_link": "Meeting Link",  # URL
    "drive_folder": "Drive Folder",  # URL
    "event_id": "Event ID",      # Rich text (для идемпотентности)
}

# Фильтры для исключения событий
EXCLUDED_KEYWORDS = [
    "день рождения",
    "день рожденья", 
    "birthday",
    "дела",
    "дело",
    "задачи",
    "задача"
]

def format_folder_name(title: str, start_iso: str) -> str:
    """Форматирует название папки в формате YYYY-MM-DD hh-mm Название встречи."""
    try:
        # Парсим время начала
        if start_iso:
            # Убираем 'Z' и парсим ISO формат
            start_str = start_iso.replace('Z', '+00:00')
            start_dt = dt.datetime.fromisoformat(start_str)
            
            # Форматируем дату и время
            date_str = start_dt.strftime("%Y-%m-%d")
            time_str = start_dt.strftime("%H-%M")
            
            # Формируем название папки
            folder_name = f"{date_str} {time_str} {title}"
            return folder_name
        else:
            # Если время не указано, используем только название
            return title
    except Exception as e:
        print(f"⚠️ Ошибка форматирования названия папки: {e}")
        return title

# ---------------------------------------------------------------------------
# Загрузка переменных окружения
# ---------------------------------------------------------------------------

def load_env_or_fail() -> Dict[str, str]:
    load_dotenv()
    need = [
        "NOTION_TOKEN",
        "NOTION_DATABASE_ID",
        # Личные ключи/пути
        "PERSONAL_CALENDAR_ID",
        "PERSONAL_GOOGLE_OAUTH_CLIENT",   # путь к credentials.json (OAuth client)
        "PERSONAL_GOOGLE_TOKEN",          # путь к token.json (будет создан при первом логине)
        "PERSONAL_DRIVE_PARENT_ID",       # ID родительской папки на Drive
    ]
    env = {}
    missing = []
    for k in need:
        v = os.getenv(k)
        if not v:
            missing.append(k)
        else:
            env[k] = v
    if missing:
        print("✖ Отсутствуют переменные в .env:\n  " + "\n  ".join(missing), file=sys.stderr)
        print("Примеры валидных путей смотрите в конце файла (DOCSTRING).", file=sys.stderr)
        sys.exit(1)

    # Опциональные
    env["TIMEZONE"] = os.getenv("TIMEZONE", "Europe/Amsterdam")
    env["DEFAULT_LOOKAHEAD_HOURS"] = os.getenv("DEFAULT_LOOKAHEAD_HOURS", "24")
    env["TELEGRAM_BOT_TOKEN"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    env["TELEGRAM_CHAT_ID"] = os.getenv("TELEGRAM_CHAT_ID", "")
    return env

# ---------------------------------------------------------------------------
# Google OAuth helpers (только для личного аккаунта)
# ---------------------------------------------------------------------------

def _credentials_from_files(client_path: str, token_path: str, scopes: List[str]) -> Credentials:
    # Safety checks for placeholder or invalid absolute paths
    if not client_path or "absolute/path" in client_path:
        print("✖ В .env указан плейсхолдер для пути OAuth client. Задайте реальный путь PERSONAL_GOOGLE_OAUTH_CLIENT.", file=sys.stderr)
        sys.exit(1)
    if not token_path or "absolute/path" in token_path:
        print("✖ В .env указан плейсхолдер для пути token.json. Задайте реальный путь PERSONAL_GOOGLE_TOKEN.", file=sys.stderr)
        sys.exit(1)

    client = _expand(client_path)
    token = _expand(token_path)

    if not client.exists():
        print(f"✖ Файл OAuth client не найден: {client}\n  Проверьте .env → PERSONAL_GOOGLE_OAUTH_CLIENT.", file=sys.stderr)
        sys.exit(1)

    token_parent = token.parent
    try:
        token_parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"✖ Не удалось создать папку для token.json: {token_parent}\n  Причина: {e}\n  Укажите путь внутри домашней папки, например: ~/repository/meeting_automation/tokens/personal_token.json", file=sys.stderr)
        sys.exit(1)

    creds: Optional[Credentials] = None
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token), scopes)
    # Если нет или истёк refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client), scopes)
            creds = flow.run_local_server(port=0)
        with open(token, "w", encoding="utf-8") as f:
            f.write(creds.to_json())
    return creds


def get_google_services(env: Dict[str, str]):
    """Возвращает calendar_service и drive_service для личного аккаунта."""
    client = env["PERSONAL_GOOGLE_OAUTH_CLIENT"]
    token = env["PERSONAL_GOOGLE_TOKEN"]

    creds = _credentials_from_files(client, token, SCOPES_PERSONAL)
    
    # Calendar сервис
    cal_svc = build("calendar", "v3", credentials=creds)
    
    # Drive сервис
    drive_svc = build("drive", "v3", credentials=creds)
    
    return cal_svc, drive_svc

# ---------------------------------------------------------------------------
# Calendar → события
# ---------------------------------------------------------------------------

def should_process_event(title: str) -> bool:
    """Проверяет, нужно ли обрабатывать событие."""
    if not title:
        return False
    
    title_lower = title.lower()
    
    # Проверяем исключающие ключевые слова
    for keyword in EXCLUDED_KEYWORDS:
        if keyword in title_lower:
            return False
    
    return True

def get_upcoming_events(cal_id: str, cal_svc, hours: int, timezone: str) -> List[Dict[str, Any]]:
    now = dt.datetime.now(dt.timezone.utc)
    time_min = now.isoformat()
    time_max = (now + dt.timedelta(hours=hours)).isoformat()

    events: List[Dict[str, Any]] = []
    try:
        res = cal_svc.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        items = res.get("items", [])
        for it in items:
            events.append(it)
    except HttpError as e:
        print(f"✖ Google Calendar API error: {e}")
    return events

# ---------------------------------------------------------------------------
# Google Drive → папки
# ---------------------------------------------------------------------------

def folder_exists(drive_svc, title: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Проверяет существование папки с таким названием."""
    try:
        # Формируем запрос поиска
        query = f"name='{title}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        # Ищем папки
        results = drive_svc.files().list(
            q=query,
            fields="files(id,name,webViewLink)",
            pageSize=1
        ).execute()
        
        files = results.get("files", [])
        if files:
            folder = files[0]
            folder_id = folder.get("id")
            folder_link = folder.get("webViewLink", "")
            print(f"📁 Найдена существующая папка: {title} (ID: {folder_id})")
            return folder_link
        
        return None
        
    except HttpError as e:
        print(f"⚠️ Ошибка при поиске папки: {e}")
        return None
    except Exception as e:
        print(f"⚠️ Неожиданная ошибка при поиске папки: {e}")
        return None

def create_drive_folder(drive_svc, title: str, parent_id: Optional[str] = None) -> Optional[str]:
    """Создаёт папку на Google Drive или возвращает существующую."""
    
    # Сначала проверяем, существует ли папка
    existing_folder = folder_exists(drive_svc, title, parent_id)
    if existing_folder:
        print(f"✅ Используем существующую папку: {title}")
        return existing_folder
    
    # Если папка не существует, создаём новую
    try:
        folder_metadata = {
            "name": title,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            folder_metadata["parents"] = [parent_id]

        folder = drive_svc.files().create(
            body=folder_metadata,
            fields="id,name,webViewLink"
        ).execute()
        
        folder_id = folder.get("id")
        folder_link = folder.get("webViewLink", "")
        
        print(f"📁 Создана новая папка на Drive: {title} (ID: {folder_id})")
        return folder_link
        
    except HttpError as e:
        print(f"✖ Google Drive API error: {e}")
        return None
    except Exception as e:
        print(f"✖ Unexpected error creating Drive folder: {e}")
        return None

# ---------------------------------------------------------------------------
# Notion → страницы
# ---------------------------------------------------------------------------

def create_or_update_notion_page(
    env: Dict[str, str],
    title: str,
    start_iso: str,
    end_iso: str,
    attendees: List[str],
    meeting_link: str,
    drive_link: str,
    event_id: str,
) -> str:
    """Создаёт или обновляет страницу в Notion с применением шаблона."""
    token = env["NOTION_TOKEN"]
    database_id = env["NOTION_DATABASE_ID"]

    # Ищем существующую страницу по Event ID
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    # Поиск по Event ID
    search_url = "https://api.notion.com/v1/databases/" + database_id + "/query"
    search_data = {
        "filter": {
            "property": NOTION_PROP["event_id"],
            "rich_text": {
                "equals": event_id
            }
        }
    }

    try:
        r = requests.post(search_url, headers=headers, json=search_data)
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:
        print(f"✖ Не удалось найти страницу в Notion: {e}")
        results = []

    if results:
        # Обновляем существующую страницу
        page_id = results[0]["id"]
        print(f"🔄 Обновляем существующую страницу: {page_id}")
        
        # Обновляем свойства
        update_url = f"https://api.notion.com/v1/pages/{page_id}"
        update_data = {
            "properties": {}
        }
        
        # Добавляем только непустые свойства
        if title:
            update_data["properties"][NOTION_PROP["title"]] = {
                "title": [{"text": {"content": title}}]
            }
        
        if start_iso:
            try:
                start_dt = dt.datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                update_data["properties"][NOTION_PROP["date"]] = {
                    "date": {"start": start_dt.isoformat()}
                }
            except:
                pass
        
        if attendees:
            update_data["properties"][NOTION_PROP["attendees"]] = {
                "rich_text": [{"text": {"content": ", ".join(attendees)}}]
            }
        
        if meeting_link:
            update_data["properties"][NOTION_PROP["meeting_link"]] = {
                "url": meeting_link
            }
        
        if drive_link:
            update_data["properties"][NOTION_PROP["drive_folder"]] = {
                "url": drive_link
            }
        
        try:
            r = requests.patch(update_url, headers=headers, json=update_data)
            r.raise_for_status()
        except Exception as e:
            print(f"✖ Не удалось обновить страницу в Notion: {e}")
        
        return page_id
    else:
        # Создаём новую страницу с шаблоном
        print(f"➕ Создаём новую страницу с шаблоном для: {title}")
        
        # Подготавливаем свойства для страницы
        properties = {
            NOTION_PROP["title"]: {
                "title": [{"text": {"content": title}}]
            },
            NOTION_PROP["calendar"]: {
                "select": {"name": "Personal"}
            },
            NOTION_PROP["event_id"]: {
                "rich_text": [{"text": {"content": event_id}}]
            }
        }
        
        # Добавляем только непустые свойства
        if start_iso:
            try:
                start_dt = dt.datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
                properties[NOTION_PROP["date"]] = {
                    "date": {"start": start_dt.isoformat()}
                }
            except:
                pass
        
        if attendees:
            properties[NOTION_PROP["attendees"]] = {
                "rich_text": [{"text": {"content": ", ".join(attendees)}}]
            }
        
        if meeting_link:
            properties[NOTION_PROP["meeting_link"]] = {
                "url": meeting_link
            }
        
        if drive_link:
            properties[NOTION_PROP["drive_folder"]] = {
                "url": drive_link
            }

        # Пытаемся использовать шаблоны, если модуль доступен
        if create_page_with_template and create_customized_template:
            try:
                # Создаем кастомизированный шаблон
                template = create_customized_template(
                    title=title,
                    start_time=start_iso or "",
                    end_time=end_iso or "",
                    attendees=attendees,
                    meeting_link=meeting_link or "",
                    drive_link=drive_link or ""
                )
                
                # Создаем страницу с шаблоном
                page_id = create_page_with_template(
                    notion_token=token,
                    database_id=database_id,
                    properties=properties,
                    template=template
                )
                
                if page_id:
                    print(f"✅ Страница создана с шаблоном: {page_id}")
                    return page_id
                else:
                    print("⚠️ Не удалось создать страницу с шаблоном, используем стандартный метод")
                    
            except Exception as e:
                print(f"⚠️ Ошибка при создании страницы с шаблоном: {e}, используем стандартный метод")
        
        # Fallback: создаем страницу стандартным способом
        try:
            create_data = {
                "parent": {"database_id": database_id},
                "properties": properties
            }
            
            r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=create_data)
            r.raise_for_status()
            page_data = r.json()
            return page_data["id"]
        except Exception as e:
            print(f"✖ Не удалось создать страницу в Notion: {e}")
            return ""

# ---------------------------------------------------------------------------
# Обработка одного события
# ---------------------------------------------------------------------------

def process_event(env: Dict[str, str], event: Dict[str, Any]) -> None:
    """Обрабатывает одно событие из календаря."""
    title = event.get("summary", "Без названия")
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
    end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
    attendees = [a.get("email", "") for a in event.get("attendees", [])]
    meeting_link = event.get("hangoutLink", "")
    event_id = event.get("id", "")

    # Создаём папку на Drive
    drive_parent_id = env.get("PERSONAL_DRIVE_PARENT_ID")
    folder_link = ""
    
    if drive_parent_id:
        # Форматируем название папки
        folder_name = format_folder_name(title, start)
        folder_link = create_drive_folder(env["drive_svc"], folder_name, drive_parent_id) or ""
    else:
        print("⚠️ PERSONAL_DRIVE_PARENT_ID не указан, папки на Drive не создаются")

    # Создаём/обновляем страницу в Notion
    page_id = create_or_update_notion_page(
        env=env,
        title=title,
        start_iso=start or "",
        end_iso=end or "",
        attendees=attendees,
        meeting_link=meeting_link or "",
        drive_link=folder_link,
        event_id=event_id or "",
    )
    
    if folder_link:
        print(f"✅ Готово: Personal | {title} | Notion page: {page_id} | Drive folder: {folder_link}")
    else:
        print(f"✅ Готово: Personal | {title} | Notion page: {page_id} | Drive: не создана")

# ---------------------------------------------------------------------------
# Orchestrator for prepare
# ---------------------------------------------------------------------------

def run_prepare(env: Dict[str, str], days: int, limit: int) -> None:
    hours = max(1, int(days) * 24)
    tz = env["TIMEZONE"]
    cal_id = env["PERSONAL_CALENDAR_ID"]

    # Получаем Google сервисы
    cal_svc, drive_svc = get_google_services(env)
    
    # Добавляем drive_svc в env для использования в process_event
    env["drive_svc"] = drive_svc

    # Получаем события
    events = get_upcoming_events(cal_id, cal_svc, hours, tz)
    
    # Фильтруем события
    filtered_events = []
    excluded_events = []
    
    for ev in events:
        title = ev.get("summary", "Без названия")
        if should_process_event(title):
            filtered_events.append(ev)
        else:
            excluded_events.append(title)
    
    # Применяем лимит к отфильтрованным событиям
    if limit:
        filtered_events = filtered_events[: int(limit)]

    total_events = len(events)
    total_filtered = len(filtered_events)
    total_excluded = len(excluded_events)
    
    print(f"📅 Найдено событий в личном календаре: {total_events}")
    print(f"✅ Событий для обработки: {total_filtered}")
    print(f"❌ Исключено событий: {total_excluded}")
    
    # Показываем исключенные события
    if excluded_events:
        print(f"\n🚫 Исключенные события:")
        for title in excluded_events[:5]:  # Показываем первые 5
            print(f"  - {title}")
        if len(excluded_events) > 5:
            print(f"  ... и еще {len(excluded_events) - 5} событий")

    # Обрабатываем каждое отфильтрованное событие
    processed_events = []
    for ev in filtered_events:
        process_event(env, ev)
        processed_events.append(ev)

    # Создаём красивый отчёт для Telegram
    telegram_report = create_telegram_report(
        total_events=total_events,
        total_filtered=total_filtered,
        total_excluded=total_excluded,
        processed_events=processed_events,
        excluded_events=excluded_events,
        days=days,
        limit=limit
    )
    
    # Отправляем отчёт в Telegram
    notify(env, telegram_report)

# ---------------------------------------------------------------------------
# Telegram уведомление (опционально)
# ---------------------------------------------------------------------------

def create_telegram_report(
    total_events: int,
    total_filtered: int,
    total_excluded: int,
    processed_events: List[Dict[str, Any]],
    excluded_events: List[str],
    days: int,
    limit: int
) -> str:
    """Создаёт красивый отчёт для Telegram."""
    
    # Эмодзи для разных статусов
    emoji_stats = "📊"
    emoji_success = "✅"
    emoji_excluded = "❌"
    emoji_processed = "📁"
    emoji_time = "⏰"
    emoji_calendar = "📅"
    
    # Заголовок отчета
    report = f"{emoji_stats} *ОТЧЕТ ОБ ОБРАБОТКЕ ВСТРЕЧ*\n\n"
    
    # Основная статистика
    report += f"{emoji_calendar} *Период:* {days} {'день' if days == 1 else 'дней'}\n"
    if limit:
        report += f"{emoji_time} *Лимит:* {limit} встреч\n"
    report += f"\n"
    
    # Статистика событий
    report += f"{emoji_stats} *СТАТИСТИКА:*\n"
    report += f"• Всего событий: {total_events}\n"
    report += f"• Обработано встреч: {total_filtered}\n"
    report += f"• Исключено событий: {total_excluded}\n\n"
    
    # Обработанные встречи
    if processed_events:
        report += f"{emoji_processed} *ОБРАБОТАННЫЕ ВСТРЕЧИ:*\n"
        for i, event in enumerate(processed_events[:10], 1):  # Показываем первые 10
            title = event.get("summary", "Без названия")
            start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
            
            if start:
                try:
                    start_str = start.replace('Z', '+00:00')
                    start_dt = dt.datetime.fromisoformat(start_str)
                    time_str = start_dt.strftime("%d.%m %H:%M")
                    report += f"{i}. {time_str} | {title}\n"
                except:
                    report += f"{i}. {title}\n"
            else:
                report += f"{i}. {title}\n"
        
        if len(processed_events) > 10:
            report += f"... и еще {len(processed_events) - 10} встреч\n"
        report += "\n"
    
    # Исключенные события
    if excluded_events:
        report += f"{emoji_excluded} *ИСКЛЮЧЕННЫЕ СОБЫТИЯ:*\n"
        for i, title in enumerate(excluded_events[:5], 1):  # Показываем первые 5
            report += f"• {title}\n"
        if len(excluded_events) > 5:
            report += f"... и еще {len(excluded_events) - 5} событий\n"
        report += "\n"
    
    # Итог
    report += f"{emoji_success} *ИТОГ:* Система успешно обработала {total_filtered} встреч"
    if total_excluded > 0:
        report += f" и исключила {total_excluded} личных событий"
    report += "."
    
    return report

def notify(env: Dict[str, str], text: str) -> None:
    token = env.get("TELEGRAM_BOT_TOKEN")
    chat_id = env.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/sendMessage",
            params={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15
        )
        r.raise_for_status()
    except Exception as e:
        print(f"⚠️  Не удалось отправить уведомление в Telegram: {e}")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Meeting Automation (только личный аккаунт)")
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # prepare
    prepare_parser = subparsers.add_parser("prepare", help="Подготовить заметки к встречам")
    prepare_parser.add_argument("--days", type=int, default=1, help="Сколько дней брать из календаря")
    prepare_parser.add_argument("--limit", type=int, default=10, help="Максимум встреч для обработки")

    # postprocess
    subparsers.add_parser("postprocess", help="Обработка записей (транскрибация и т.п.)")

    # watch
    subparsers.add_parser("watch", help="Непрерывный режим")

    args = parser.parse_args()

    if args.cmd == "prepare":
        run_prepare(load_env_or_fail(), args.days, args.limit)
    elif args.cmd == "postprocess":
        print("Запускаем postprocess…")
    elif args.cmd == "watch":
        print("Запускаем watch…")

if __name__ == "__main__":
    main()
