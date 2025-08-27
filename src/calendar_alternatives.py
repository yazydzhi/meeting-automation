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
    event_id: str = ""
    
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
                    calendar_source='google_api',
                    event_id=event.get('id', '')
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
            # Настройки для обхода SSL проблем
            session = requests.Session()
            session.verify = False  # Отключаем SSL верификацию для тестирования
            
            # Добавляем заголовки для имитации браузера
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            logger.info(f"🔗 Загружаю календарь: {self.calendar_url}")
            response = session.get(self.calendar_url, headers=headers, timeout=60)
            
            if response.status_code != 200:
                logger.error(f"Ошибка загрузки календаря: {response.status_code}")
                logger.error(f"Заголовки ответа: {dict(response.headers)}")
                return []
            
            logger.info(f"✅ Календарь загружен успешно: {len(response.text)} символов")
            
            if self.calendar_type == 'ical':
                return self._parse_ical(response.text, start_date, end_date)
            elif self.calendar_type == 'rss':
                return self._parse_rss(response.text, start_date, end_date)
            else:
                logger.error(f"Неподдерживаемый тип календаря: {self.calendar_type}")
                return []
                
        except requests.exceptions.SSLError as e:
            logger.error(f"SSL ошибка при загрузке календаря: {e}")
            logger.info("🔄 Пробую загрузить без SSL верификации...")
            try:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                
                response = requests.get(self.calendar_url, verify=False, timeout=60)
                if response.status_code == 200:
                    logger.info(f"✅ Календарь загружен без SSL верификации: {len(response.text)} символов")
                    if self.calendar_type == 'ical':
                        return self._parse_ical(response.text, start_date, end_date)
                    elif self.calendar_type == 'rss':
                        return self._parse_rss(response.text, start_date, end_date)
                else:
                    logger.error(f"Ошибка загрузки без SSL: {response.status_code}")
                    return []
            except Exception as e2:
                logger.error(f"Ошибка загрузки без SSL: {e2}")
                return []
        except requests.exceptions.Timeout as e:
            logger.error(f"Таймаут при загрузке календаря: {e}")
            logger.info("🔄 Пробую загрузить с увеличенным таймаутом...")
            try:
                response = requests.get(self.calendar_url, verify=False, timeout=120)
                if response.status_code == 200:
                    logger.info(f"✅ Календарь загружен с увеличенным таймаутом: {len(response.text)} символов")
                    if self.calendar_type == 'ical':
                        return self._parse_ical(response.text, start_date, end_date)
                    elif self.calendar_type == 'rss':
                        return self._parse_rss(response.text, start_date, end_date)
                else:
                    logger.error(f"Ошибка загрузки с увеличенным таймаутом: {response.status_code}")
                    return []
            except Exception as e2:
                logger.error(f"Ошибка загрузки с увеличенным таймаутом: {e2}")
                return []
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с календарем: {e}")
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
        event_count = 0
        parsed_count = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line == 'BEGIN:VEVENT':
                in_event = True
                current_event = {}
                event_count += 1
            elif line == 'END:VEVENT':
                if in_event:
                    try:
                        # Обрабатываем повторяющиеся события
                        if 'RRULE' in current_event:
                            logger.info(f"📔 Найдено RRULE событие: {current_event.get('SUMMARY', 'Без названия')}")
                            logger.debug(f"📔 RRULE данные события: {current_event}")
                            rrule_events = self._expand_rrule_event(current_event, start_date, end_date)
                            logger.info(f"📔 Сгенерировано {len(rrule_events)} повторений для RRULE события")
                            for event in rrule_events:
                                if event:
                                    events.append(event)
                                    parsed_count += 1
                        elif self._is_event_in_range(current_event, start_date, end_date):
                            event = self._create_event_from_ical(current_event)
                            if event:
                                events.append(event)
                                parsed_count += 1
                        else:
                            # Логируем события вне диапазона для диагностики
                            if 'SUMMARY' in current_event and 'DTSTART' in current_event:
                                try:
                                    event_start = self._parse_ical_datetime(current_event['DTSTART'])
                                    logger.debug(f"Событие вне диапазона: {current_event['SUMMARY']} | {event_start}")
                                except:
                                    logger.debug(f"Событие вне диапазона (ошибка парсинга): {current_event.get('SUMMARY', 'Без названия')}")
                    except Exception as e:
                        logger.error(f"Ошибка обработки события: {e}")
                        logger.error(f"Данные события: {current_event}")
                in_event = False
            elif in_event and ':' in line:
                key, value = line.split(':', 1)
                
                # Обрабатываем многострочные значения (RFC 5545)
                # Проверяем следующие строки на продолжение (начинаются с пробела или табуляции)
                j = i + 1
                while j < len(lines) and len(lines[j]) > 0 and lines[j][0] in ' \t':
                    value += lines[j][1:]  # Убираем первый символ (пробел/таб) и добавляем к значению
                    j += 1
                i = j - 1  # Устанавливаем индекс на последнюю обработанную строку
                
                current_event[key] = value
            
            i += 1
        
        logger.info(f"📊 iCal парсинг: найдено {event_count} событий, в диапазоне {parsed_count}")
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
        try:
            # Убираем возможные параметры (TZID, VALUE и т.д.)
            if ';' in dt_string:
                # Разбираем параметры
                parts = dt_string.split(';')
                dt_string = parts[-1]  # Берем последнюю часть - саму дату
            
            # Убираем возможные кавычки
            dt_string = dt_string.strip('"')
            
            # Парсим различные форматы дат
            if len(dt_string) == 8:  # YYYYMMDD
                return datetime.strptime(dt_string, '%Y%m%d')
            elif len(dt_string) == 15:  # YYYYMMDDTHHMMSS
                return datetime.strptime(dt_string, '%Y%m%dT%H%M%S')
            elif len(dt_string) == 16:  # YYYYMMDDTHHMMSSZ
                return datetime.strptime(dt_string, '%Y%m%dT%H%M%SZ')
            elif len(dt_string) == 19:  # YYYYMMDDTHHMMSS (без Z)
                return datetime.strptime(dt_string, '%Y%m%dT%H%M%S')
            elif len(dt_string) == 20:  # YYYYMMDDTHHMMSS (с TZID)
                # Убираем TZID если есть
                if 'T' in dt_string:
                    dt_part = dt_string.split('T')[0] + 'T' + dt_string.split('T')[1]
                    return datetime.strptime(dt_part, '%Y%m%dT%H%M%S')
                else:
                    return datetime.strptime(dt_string, '%Y%m%dT%H%M%S')
            else:
                # Попробуем парсить как ISO формат
                try:
                    return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
                except:
                    raise ValueError(f"Неподдерживаемый формат даты: {dt_string}")
        except Exception as e:
            logger.error(f"Ошибка парсинга даты '{dt_string}': {e}")
            raise
    
    def _create_event_from_ical(self, event_data: Dict[str, str]) -> Optional[CalendarEvent]:
        """Создать событие из данных iCal."""
        try:
            title = event_data.get('SUMMARY', 'Без названия')
            start = self._parse_ical_datetime(event_data.get('DTSTART', ''))
            end = self._parse_ical_datetime(event_data.get('DTEND', ''))
            description = event_data.get('DESCRIPTION', '')
            location = event_data.get('LOCATION', '')
            
            # Извлекаем участников из iCal с более детальной информацией
            attendees = []
            attendee_mapping = {}  # Словарь для сопоставления частичных имен и полных email
            
            for key, value in event_data.items():
                if key.startswith('ATTENDEE') or '@' in value:
                    # Убираем параметры и оставляем только email
                    if ':' in value:
                        email = value.split(':', 1)[1]
                        # Убираем mailto: если есть
                        if email.startswith('mailto:'):
                            email = email[7:]
                        # Убираем дополнительные параметры
                        if ';' in email:
                            email = email.split(';')[0]
                        
                        # Если это частичное имя (например, hev@cian.ru), сохраняем для сопоставления
                        if '@' in email and '.' not in email.split('@')[0]:
                            # Это частичное имя, ищем полный email
                            for k, v in event_data.items():
                                if 'mailto:' in v and email.split('@')[0] in v:
                                    full_email = v.split('mailto:')[1].split(';')[0]
                                    attendee_mapping[email] = full_email
                                    if full_email not in attendees:
                                        attendees.append(full_email)
                                    break
                        else:
                            # Это полный email
                            if email not in attendees:
                                attendees.append(email)
            
            # Также ищем участников в других полях
            for key, value in event_data.items():
                if '@' in value and 'mailto:' in value:
                    email = value.split('mailto:')[1].split(';')[0]
                    if email not in attendees:
                        attendees.append(email)
            
            # Извлекаем ссылку на встречу
            meeting_link = ""
            for key, value in event_data.items():
                if key.startswith('X-GOOGLE-CONFERENCE') or 'meet.google.com' in value or 'zoom.us' in value:
                    meeting_link = value
                    break
            
            # Генерируем уникальный ID для события на основе его данных
            event_id = f"{start.strftime('%Y%m%d%H%M')}_{hash(title)}"
            
            return CalendarEvent(
                title=title,
                start=start,
                end=end,
                description=description,
                location=location,
                attendees=attendees,
                meeting_link=meeting_link,
                calendar_source='web_ical',
                event_id=event_id
            )
        except Exception as e:
            logger.error(f"Ошибка создания события из iCal: {e}")
            return None
    
    def _expand_rrule_event(self, event_data: Dict[str, str], start_date: datetime, end_date: datetime) -> List[CalendarEvent]:
        """Расширить повторяющееся событие (RRULE) в конкретные события."""
        events = []
        event_name = event_data.get('SUMMARY', 'Без названия')
        
        try:
            # Ищем DTSTART с возможными параметрами
            dtstart_key = None
            for key in event_data.keys():
                if key.startswith('DTSTART'):
                    dtstart_key = key
                    break
            
            if not dtstart_key or 'RRULE' not in event_data:
                logger.debug(f"RRULE событие '{event_name}' не содержит DTSTART или RRULE")
                logger.debug(f"RRULE ключи: {list(event_data.keys())}")
                return events
            
            # Парсим начальную дату события
            event_start = self._parse_ical_datetime(event_data[dtstart_key])
            logger.debug(f"RRULE '{event_name}': исходная дата {event_start}")
            logger.debug(f"RRULE '{event_name}': искомый диапазон {start_date} - {end_date}")
            
            # Ищем DTEND с возможными параметрами
            dtend_key = None
            for key in event_data.keys():
                if key.startswith('DTEND'):
                    dtend_key = key
                    break
            
            # Вычисляем продолжительность события
            if dtend_key:
                event_end = self._parse_ical_datetime(event_data[dtend_key])
                duration = event_end - event_start
            else:
                duration = timedelta(hours=1)  # По умолчанию 1 час
            
            # Простой парсинг RRULE для основных случаев
            rrule = event_data['RRULE']
            logger.debug(f"RRULE '{event_name}': правило {rrule}")
            
            # Извлекаем параметры RRULE
            freq = None
            interval = 1
            until = None
            byday = None
            
            for param in rrule.split(';'):
                if param.startswith('FREQ='):
                    freq = param.split('=')[1]
                elif param.startswith('INTERVAL='):
                    interval = int(param.split('=')[1])
                elif param.startswith('UNTIL='):
                    until_str = param.split('=')[1]
                    try:
                        until = self._parse_ical_datetime(until_str)
                    except:
                        until = None
                elif param.startswith('BYDAY='):
                    byday = param.split('=')[1]
            
            if not freq:
                logger.debug(f"RRULE '{event_name}': частота не найдена")
                return events
            
            logger.debug(f"RRULE '{event_name}': FREQ={freq}, INTERVAL={interval}, UNTIL={until}, BYDAY={byday}")
            
            # Начинаем поиск с более раннего времени для захвата повторений
            search_start = max(event_start, start_date - timedelta(days=365))  # Ищем год назад
            current_start = search_start
            max_iterations = 500  # Увеличиваем лимит итераций
            iteration = 0
            
            while current_start <= end_date and iteration < max_iterations:
                iteration += 1
                
                # Проверяем, что событие попадает в диапазон
                if current_start >= start_date:
                    logger.debug(f"RRULE '{event_name}': добавляем событие на {current_start}")
                    
                    # Создаем копию данных события с новой датой
                    new_event_data = event_data.copy()
                    
                    # Обновляем даты
                    new_start_str = current_start.strftime('%Y%m%dT%H%M%S')
                    new_end_str = (current_start + duration).strftime('%Y%m%dT%H%M%S')
                    
                    new_event_data['DTSTART'] = new_start_str
                    new_event_data['DTEND'] = new_end_str
                    
                    # Удаляем RRULE из копии
                    new_event_data.pop('RRULE', None)
                    
                    event = self._create_event_from_ical(new_event_data)
                    if event:
                        events.append(event)
                
                # Вычисляем следующую дату
                if freq == 'DAILY':
                    current_start += timedelta(days=interval)
                elif freq == 'WEEKLY':
                    current_start += timedelta(weeks=interval)
                elif freq == 'MONTHLY':
                    # Простая логика для месячных повторений
                    try:
                        if current_start.month == 12:
                            current_start = current_start.replace(year=current_start.year + 1, month=1)
                        else:
                            current_start = current_start.replace(month=current_start.month + 1)
                    except ValueError:
                        # Если день не существует в новом месяце (например, 31 февраля)
                        current_start += timedelta(days=30)
                else:
                    logger.debug(f"RRULE '{event_name}': неподдерживаемая частота {freq}")
                    break  # Неподдерживаемая частота
                
                # Проверяем UNTIL
                if until and current_start > until:
                    logger.debug(f"RRULE '{event_name}': достигнута дата окончания {until}")
                    break
            
            logger.debug(f"RRULE '{event_name}': сгенерировано {len(events)} повторений за {iteration} итераций")
            
        except Exception as e:
            logger.error(f"Ошибка расширения RRULE для '{event_name}': {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return events

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
        web_provider = WebCalendarProvider("file://local", "ical")
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
