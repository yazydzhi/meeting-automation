

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_notion_db.py
-------------------
Создаёт базу данных Notion для meeting_automation и печатает её DATABASE_ID.

Требуется .env с:
  NOTION_TOKEN=secret_xxx
  NOTION_PARENT_PAGE_ID=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  # страница, куда прикрепится база

Опционально:
  NOTION_DB_TITLE="Meeting Notes"   # заголовок БД

Запуск:
  python create_notion_db.py
  python create_notion_db.py --title "My Meetings"
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from typing import Dict, Any

import requests
from dotenv import load_dotenv

NOTION_API_URL = "https://api.notion.com/v1/databases"
NOTION_VERSION = "2022-06-28"

DEFAULT_PROPERTIES: Dict[str, Any] = {
    "Name": {"title": {}},
    "Date": {"date": {}},
    "Calendar": {
        "select": {
            "options": [
                {"name": "Work", "color": "blue"},
                {"name": "Personal", "color": "green"}
            ]
        }
    },
    "Attendees": {"rich_text": {}},
    "Meeting Link": {"url": {}},
    "Drive Folder": {"url": {}},
    "Event ID": {"rich_text": {}}
}


def create_database(token: str, parent_page_id: str, title: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    payload = {
        "parent": {"type": "page_id", "page_id": parent_page_id},
        "title": [
            {
                "type": "text",
                "text": {"content": title}
            }
        ],
        "properties": DEFAULT_PROPERTIES,
    }

    resp = requests.post(NOTION_API_URL, headers=headers, data=json.dumps(payload), timeout=30)
    if resp.status_code not in (200, 201):
        print("✖ Не удалось создать базу данных в Notion.")
        print(f"Status: {resp.status_code}")
        try:
            print(resp.json())
        except Exception:
            print(resp.text)
        sys.exit(1)

    data = resp.json()
    db_id = data.get("id")
    if not db_id:
        print("✖ В ответе нет id базы.")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        sys.exit(1)

    print("✅ База данных создана.")
    print(f"NOTION_DATABASE_ID={db_id}")
    return db_id


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Create Notion database for meeting automation")
    parser.add_argument("--title", default=os.getenv("NOTION_DB_TITLE", "Meeting Notes"), help="Database title")
    args = parser.parse_args()

    token = os.getenv("NOTION_TOKEN")
    parent = os.getenv("NOTION_PARENT_PAGE_ID")

    missing = []
    if not token:
        missing.append("NOTION_TOKEN")
    if not parent:
        missing.append("NOTION_PARENT_PAGE_ID")

    if missing:
        print("✖ Не заданы переменные в .env:\n  " + "\n  ".join(missing), file=sys.stderr)
        sys.exit(1)

    create_database(token, parent, args.title)


if __name__ == "__main__":
    main()