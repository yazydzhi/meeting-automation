#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Альтернативные способы получения данных календаря
"""

import os
import re
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class CalendarEvent:
    """Структура события календаря."""
    title: str
    start: datetime
    end: datetime
    description: str = ""
    location: str = ""
    attendees: List[str] = None
    meeting_link: str = ""
    calendar_source: str = "unknown"
    
    def __post_init__(self):
        if self.attendees is None:
            self.attendees = []

class CalendarProvider:
    """Базовый класс для провайдеров календаря."""
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Получить события за период."""
        raise NotImplementedError
    
    def get_today_events(self) -> List[CalendarEvent]:
        """Получить события на сегодня."""
        today = datetime.now().date()
        start = datetime.combine(today, datetime.min.time())
        end = datetime.combine(today, datetime.max.time())
        return self.get_events(start, end)
    
    def get_upcoming_events(self, days: int = 7) -> List[CalendarEvent]:
        """Получить предстоящие события."""
        start = datetime.now()
        end = start + timedelta(days=days)
        return self.get_events(start, end)

class GoogleCalendarAPIProvider(CalendarProvider):
    """Стандартный провайдер Google Calendar API."""
    
    def __init__(self, credentials_path: str, calendar_id: str):
        self.credentials_path = credentials_path
        self.calendar_id = calendar_id
        self.service = None
    
    def _get_service(self):
        """Получить Google Calendar сервис."""
        if self.service is None:
            try:
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                
                if os.path.exists(self.credentials_path):
                    creds = Credentials.from_authorized_user_file(self.credentials_path)
                    self.service = build('calendar', 'v3', credentials=creds)
                else:
                    logger.error(f"Файл учетных данных не найден: {self.credentials_path}")
                    return None
            except Exception as e:
                logger.error(f"Ошибка инициализации Google Calendar API: {e}")
                return None
        return self.service
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Получить события через Google Calendar API."""
        service = self._get_service()
        if not service:
            return []
        
        try:
            events_result = service.events().list(
                calendarId=self.calendar_id,
                timeMin=start_date.isoformat() + 'Z',
                timeMax=end_date.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            calendar_events = []
            
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Парсим время
                if 'T' in start:
                    start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
                else:
                    start_dt = datetime.fromisoformat(start)
                    end_dt = datetime.fromisoformat(end)
                
                # Получаем участников
                attendees = []
                if 'attendees' in event:
                    attendees = [att.get('email', '') for att in event['attendees']]
                
                # Получаем ссылку на встречу
                meeting_link = ""
                if 'hangoutLink' in event:
                    meeting_link = event['hangoutLink']
                elif 'conferenceData' in event:
                    meeting_link = event['conferenceData'].get('entryPoints', [{}])[0].get('uri', '')
                
                calendar_event = CalendarEvent(
                    title=event.get('summary', 'Без названия'),
                    start=start_dt,
                    end=end_dt,
                    description=event.get('description', ''),
                    location=event.get('location', ''),
                    attendees=attendees,
                    meeting_link=meeting_link,
                    calendar_source='google_api'
                )
                calendar_events.append(calendar_event)
            
            return calendar_events
            
        except Exception as e:
            logger.error(f"Ошибка получения событий через Google Calendar API: {e}")
            return []

class NotionCalendarProvider(CalendarProvider):
    """Провайдер календаря через Notion."""
    
    def __init__(self, notion_token: str, database_id: str):
        self.notion_token = notion_token
        self.database_id = database_id
        self.headers = {
            'Authorization': f'Bearer {notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Получить события через Notion базу данных."""
        try:
            # Формируем фильтр по дате
            filter_data = {
                "filter": {
                    "and": [
                        {
                            "property": "Дата",
                            "date": {
                                "on_or_after": start_date.date().isoformat()
                            }
                        },
                        {
                            "property": "Дата",
                            "date": {
                                "on_or_before": end_date.date().isoformat()
                            }
                        }
                    ]
                }
            }
            
            response = requests.post(
                f'https://api.notion.com/v1/databases/{self.database_id}/query',
                headers=self.headers,
                json=filter_data
            )
            
            if response.status_code != 200:
                logger.error(f"Ошибка запроса к Notion: {response.status_code}")
                return []
            
            data = response.json()
            events = []
            
            for page in data.get('results', []):
                properties = page.get('properties', {})
                
                # Извлекаем данные события
                title = properties.get('Название', {}).get('title', [{}])[0].get('plain_text', 'Без названия')
                
                # Парсим дату
                date_prop = properties.get('Дата', {}).get('date', {})
                if date_prop and date_prop.get('start'):
                    start_str = date_prop['start']
                    if 'T' in start_str:
                        start_dt = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                        end_dt = start_dt + timedelta(hours=1)  # По умолчанию 1 час
                    else:
                        start_dt = datetime.fromisoformat(start_str)
                        end_dt = start_dt + timedelta(hours=1)
                else:
                    continue
                
                # Описание
                description = properties.get('Описание', {}).get('rich_text', [{}])[0].get('plain_text', '')
                
                # Место
                location = properties.get('Место', {}).get('rich_text', [{}])[0].get('plain_text', '')
                
                # Участники
                attendees = []
                attendees_prop = properties.get('Участники', {}).get('multi_select', [])
                attendees = [item.get('name', '') for item in attendees_prop]
                
                # Ссылка на встречу
                meeting_link = properties.get('Ссылка', {}).get('url', '')
                
                event = CalendarEvent(
                    title=title,
                    start=start_dt,
                    end=end_dt,
                    description=description,
                    location=location,
                    attendees=attendees,
                    meeting_link=meeting_link,
                    calendar_source='notion'
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка получения событий через Notion: {e}")
            return []

class WebCalendarProvider(CalendarProvider):
    """Провайдер календаря через веб-ссылки (iCal, RSS)."""
    
    def __init__(self, calendar_url: str, calendar_type: str = 'ical'):
        self.calendar_url = calendar_url
        self.calendar_type = calendar_type
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Получить события через веб-календарь."""
        try:
            response = requests.get(self.calendar_url)
            if response.status_code != 200:
                logger.error(f"Ошибка загрузки календаря: {response.status_code}")
                return []
            
            if self.calendar_type == 'ical':
                return self._parse_ical(response.text, start_date, end_date)
            elif self.calendar_type == 'rss':
                return self._parse_rss(response.text, start_date, end_date)
            else:
                logger.error(f"Неподдерживаемый тип календаря: {self.calendar_type}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка получения событий через веб-календарь: {e}")
            return []
    
    def _parse_ical(self, content: str, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Парсинг iCal формата."""
        events = []
        lines = content.split('\n')
        
        current_event = {}
        in_event = False
        
        for line in lines:
            line = line.strip()
            
            if line == 'BEGIN:VEVENT':
                in_event = True
                current_event = {}
            elif line == 'END:VEVENT':
                if in_event and self._is_event_in_range(current_event, start_date, end_date):
                    event = self._create_event_from_ical(current_event)
                    if event:
                        events.append(event)
                in_event = False
            elif in_event and ':' in line:
                key, value = line.split(':', 1)
                current_event[key] = value
        
        return events
    
    def _parse_rss(self, content: str, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Парсинг RSS формата."""
        # Простая реализация RSS парсинга
        events = []
        # TODO: Реализовать RSS парсинг
        return events
    
    def _is_event_in_range(self, event_data: Dict[str, str], start_date: datetime, end_date: datetime) -> bool:
        """Проверить, находится ли событие в заданном диапазоне."""
        if 'DTSTART' not in event_data:
            return False
        
        try:
            event_start = self._parse_ical_datetime(event_data['DTSTART'])
            return start_date <= event_start <= end_date
        except:
            return False
    
    def _parse_ical_datetime(self, dt_string: str) -> datetime:
        """Парсинг даты из iCal формата."""
        # Убираем возможные параметры
        if ';' in dt_string:
            dt_string = dt_string.split(';')[1]
        
        # Парсим дату
        if len(dt_string) == 8:  # YYYYMMDD
            return datetime.strptime(dt_string, '%Y%m%d')
        elif len(dt_string) == 15:  # YYYYMMDDTHHMMSS
            return datetime.strptime(dt_string, '%Y%m%dT%H%M%S')
        elif len(dt_string) == 16:  # YYYYMMDDTHHMMSSZ
            return datetime.strptime(dt_string, '%Y%m%dT%H%M%SZ')
        else:
            raise ValueError(f"Неподдерживаемый формат даты: {dt_string}")
    
    def _create_event_from_ical(self, event_data: Dict[str, str]) -> Optional[CalendarEvent]:
        """Создать событие из данных iCal."""
        try:
            title = event_data.get('SUMMARY', 'Без названия')
            start = self._parse_ical_datetime(event_data.get('DTSTART', ''))
            end = self._parse_ical_datetime(event_data.get('DTEND', ''))
            description = event_data.get('DESCRIPTION', '')
            location = event_data.get('LOCATION', '')
            
            return CalendarEvent(
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                calendar_source='web_ical'
            )
        except Exception as e:
            logger.error(f"Ошибка создания события из iCal: {e}")
            return None

class LocalCalendarProvider(CalendarProvider):
    """Провайдер календаря из локальных файлов."""
    
    def __init__(self, calendar_file: str):
        self.calendar_file = calendar_file
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Получить события из локального файла календаря."""
        if not os.path.exists(self.calendar_file):
            logger.error(f"Файл календаря не найден: {self.calendar_file}")
            return []
        
        try:
            with open(self.calendar_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Определяем тип файла по расширению
            if self.calendar_file.endswith('.ics'):
                return self._parse_ical(content, start_date, end_date)
            elif self.calendar_file.endswith('.json'):
                return self._parse_json(content, start_date, end_date)
            else:
                logger.error(f"Неподдерживаемый формат файла: {self.calendar_file}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка чтения локального календаря: {e}")
            return []
    
    def _parse_ical(self, content: str, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Парсинг iCal содержимого."""
        # Используем WebCalendarProvider для парсинга
        web_provider = WebCalendarProvider("", "ical")
        return web_provider._parse_ical(content, start_date, end_date)
    
    def _parse_json(self, content: str, start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Парсинг JSON формата."""
        try:
            data = json.loads(content)
            events = []
            
            for event_data in data.get('events', []):
                try:
                    start = datetime.fromisoformat(event_data['start'])
                    end = datetime.fromisoformat(event_data['end'])
                    
                    if start_date <= start <= end_date:
                        event = CalendarEvent(
                            title=event_data.get('title', 'Без названия'),
                            start=start,
                            end=end,
                            description=event_data.get('description', ''),
                            location=event_data.get('location', ''),
                            attendees=event_data.get('attendees', []),
                            meeting_link=event_data.get('meeting_link', ''),
                            calendar_source='local_json'
                        )
                        events.append(event)
                except Exception as e:
                    logger.warning(f"Ошибка парсинга события: {e}")
                    continue
            
            return events
            
        except Exception as e:
            logger.error(f"Ошибка парсинга JSON: {e}")
            return []

def get_calendar_provider(provider_type: str, **kwargs) -> CalendarProvider:
    """Фабрика для создания провайдеров календаря."""
    
    if provider_type == 'google_api':
        return GoogleCalendarAPIProvider(
            kwargs.get('credentials_path', ''),
            kwargs.get('calendar_id', '')
        )
    elif provider_type == 'notion':
        return NotionCalendarProvider(
            kwargs.get('notion_token', ''),
            kwargs.get('database_id', '')
        )
    elif provider_type == 'web_ical':
        return WebCalendarProvider(
            kwargs.get('calendar_url', ''),
            'ical'
        )
    elif provider_type == 'web_rss':
        return WebCalendarProvider(
            kwargs.get('calendar_url', ''),
            'rss'
        )
    elif provider_type == 'local_ics':
        return LocalCalendarProvider(
            kwargs.get('calendar_file', '')
        )
    elif provider_type == 'local_json':
        return LocalCalendarProvider(
            kwargs.get('calendar_file', '')
        )
    else:
        raise ValueError(f"Неизвестный тип провайдера календаря: {provider_type}")

def get_calendar_events(provider_type: str, start_date: datetime, end_date: datetime, **kwargs) -> List[CalendarEvent]:
    """Удобная функция для получения событий календаря."""
    provider = get_calendar_provider(provider_type, **kwargs)
    return provider.get_events(start_date, end_date)
