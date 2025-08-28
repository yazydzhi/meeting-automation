#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Обработчик для работы с календарями (Google Calendar, Outlook, iCal)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from .base_handler import BaseHandler, retry

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    GOOGLE_CALENDAR_AVAILABLE = False

try:
    import icalendar
    import requests
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False


class CalendarHandler(BaseHandler):
    """Обработчик для работы с календарями."""
    
    def __init__(self, config_manager, logger=None):
        """
        Инициализация обработчика календаря.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.google_service = None
        self.calendar_cache = {}
        
    def get_calendar_events(self, account_type: str, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """
        Получает события календаря для указанного аккаунта.
        
        Args:
            account_type: Тип аккаунта ('personal' или 'work')
            days_ahead: Количество дней вперед для поиска событий
            
        Returns:
            Список событий календаря
        """
        try:
            self.logger.info(f"📅 Получение событий календаря для {account_type} на {days_ahead} дней вперед")
            
            # Получаем конфигурацию аккаунта
            account_config = self._get_account_config(account_type)
            if not account_config:
                self.logger.error(f"❌ Конфигурация для аккаунта {account_type} не найдена")
                return []
            
            calendar_provider = account_config.get('calendar_provider', 'web_ical')
            
            if calendar_provider == 'google' and GOOGLE_CALENDAR_AVAILABLE:
                return self._get_google_calendar_events(account_config, days_ahead)
            elif calendar_provider == 'web_ical' and ICAL_AVAILABLE:
                return self._get_ical_calendar_events(account_config, days_ahead)
            else:
                self.logger.warning(f"⚠️ Провайдер календаря {calendar_provider} не поддерживается")
                return self._get_sample_events(account_type, days_ahead)
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения событий календаря: {e}")
            return []
    
    def _get_google_calendar_events(self, account_config: Dict[str, Any], days_ahead: int) -> List[Dict[str, Any]]:
        """
        Получает события из Google Calendar.
        
        Args:
            account_config: Конфигурация аккаунта
            days_ahead: Количество дней вперед
            
        Returns:
            Список событий Google Calendar
        """
        try:
            # Инициализируем Google Calendar API
            if not self.google_service:
                self._init_google_calendar(account_config)
            
            if not self.google_service:
                return []
            
            # Получаем события
            now = datetime.utcnow().isoformat() + 'Z'
            end_time = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            events_result = self.google_service.events().list(
                calendarId='primary',
                timeMin=now,
                timeMax=end_time,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Преобразуем в стандартный формат
            formatted_events = []
            for event in events:
                formatted_event = self._format_google_event(event)
                if formatted_event:
                    formatted_events.append(formatted_event)
            
            self.logger.info(f"✅ Получено {len(formatted_events)} событий из Google Calendar")
            return formatted_events
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения событий Google Calendar: {e}")
            return []
    
    def _get_ical_calendar_events(self, account_config: Dict[str, Any], days_ahead: int) -> List[Dict[str, Any]]:
        """
        Получает события из iCal календаря.
        
        Args:
            account_config: Конфигурация аккаунта
            days_ahead: Количество дней вперед
            
        Returns:
            Список событий iCal календаря
        """
        try:
            ical_url = account_config.get('ical_calendar_url')
            if not ical_url:
                self.logger.warning("⚠️ URL iCal календаря не указан")
                return []
            
            # Загружаем iCal календарь
            response = requests.get(ical_url, timeout=30)
            response.raise_for_status()
            
            # Парсим iCal
            cal = icalendar.Calendar.from_ical(response.content)
            
            # Получаем события
            now = datetime.now()
            end_time = now + timedelta(days=days_ahead)
            
            events = []
            for component in cal.walk():
                if component.name == "VEVENT":
                    event = self._format_ical_event(component, now, end_time)
                    if event:
                        events.append(event)
            
            self.logger.info(f"✅ Получено {len(events)} событий из iCal календаря")
            return events
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения событий iCal календаря: {e}")
            return []
    
    def _format_google_event(self, event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Форматирует событие Google Calendar в стандартный формат.
        
        Args:
            event: Событие Google Calendar
            
        Returns:
            Отформатированное событие или None
        """
        try:
            # Извлекаем основную информацию
            event_id = event.get('id', '')
            title = event.get('summary', 'Unknown Event')
            
            # Обрабатываем время
            start_time = event.get('start', {}).get('dateTime') or event.get('start', {}).get('date')
            end_time = event.get('end', {}).get('dateTime') or event.get('end', {}).get('date')
            
            if not start_time:
                return None
            
            # Обрабатываем участников
            attendees = []
            if 'attendees' in event:
                for attendee in event['attendees']:
                    if attendee.get('responseStatus') != 'declined':
                        attendees.append(attendee.get('email', 'Unknown'))
            
            # Формируем стандартный формат
            formatted_event = {
                'id': event_id,
                'title': title,
                'start': start_time,
                'end': end_time,
                'attendees': attendees,
                'attendees_count': len(attendees),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'html_link': event.get('htmlLink', ''),
                'source': 'google_calendar'
            }
            
            return formatted_event
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка форматирования события Google Calendar: {e}")
            return None
    
    def _format_ical_event(self, component, now: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
        """
        Форматирует событие iCal в стандартный формат.
        
        Args:
            component: Компонент iCal события
            now: Текущее время
            end_time: Время окончания периода поиска
            
        Returns:
            Отформатированное событие или None
        """
        try:
            # Извлекаем время события
            start_dt = component.get('dtstart')
            end_dt = component.get('dtend')
            
            if not start_dt:
                return None
            
            # Преобразуем в datetime
            if hasattr(start_dt.dt, 'date'):
                start_time = start_dt.dt.isoformat()
            else:
                start_time = start_dt.dt.isoformat()
            
            if end_dt:
                if hasattr(end_dt.dt, 'date'):
                    end_time_event = end_dt.dt.isoformat()
                else:
                    end_time_event = end_dt.dt.isoformat()
            else:
                # Если время окончания не указано, добавляем 1 час
                start_dt_obj = start_dt.dt if hasattr(start_dt.dt, 'date') else start_dt.dt
                end_time_event = (start_dt_obj + timedelta(hours=1)).isoformat()
            
            # Проверяем, что событие в нужном диапазоне
            event_start = start_dt.dt if hasattr(start_dt.dt, 'date') else start_dt.dt
            if event_start < now or event_start > end_time:
                return None
            
            # Извлекаем основную информацию
            title = str(component.get('summary', 'Unknown Event'))
            description = str(component.get('description', ''))
            location = str(component.get('location', ''))
            
            # Обрабатываем участников
            attendees = []
            if 'attendee' in component:
                for attendee in component['attendee']:
                    email = str(attendee).replace('mailto:', '')
                    attendees.append(email)
            
            # Формируем стандартный формат
            formatted_event = {
                'id': f"ical_{hash(start_time + title)}",
                'title': title,
                'start': start_time,
                'end': end_time_event,
                'attendees': attendees,
                'attendees_count': len(attendees),
                'description': description,
                'location': location,
                'source': 'ical_calendar'
            }
            
            return formatted_event
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка форматирования события iCal: {e}")
            return None
    
    def _init_google_calendar(self, account_config: Dict[str, Any]):
        """
        Инициализирует Google Calendar API.
        
        Args:
            account_config: Конфигурация аккаунта
        """
        try:
            credentials_path = account_config.get('google_credentials')
            if not credentials_path or not os.path.exists(credentials_path):
                self.logger.warning("⚠️ Файл учетных данных Google не найден")
                return
            
            # Загружаем учетные данные
            creds = None
            if os.path.exists('token.json'):
                creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/calendar.readonly'])
            
            # Если нет действительных учетных данных, запрашиваем авторизацию
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, ['https://www.googleapis.com/auth/calendar.readonly'])
                    creds = flow.run_local_server(port=0)
                
                # Сохраняем учетные данные
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
            
            # Создаем сервис
            self.google_service = build('calendar', 'v3', credentials=creds)
            self.logger.info("✅ Google Calendar API инициализирован")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации Google Calendar API: {e}")
            self.google_service = None
    
    def _get_account_config(self, account_type: str) -> Optional[Dict[str, Any]]:
        """
        Получает конфигурацию аккаунта.
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Конфигурация аккаунта или None
        """
        try:
            if account_type == 'personal':
                return self.config_manager.get_personal_config()
            elif account_type == 'work':
                return self.config_manager.get_work_config()
            else:
                return None
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигурации аккаунта {account_type}: {e}")
            return None
    
    def _get_sample_events(self, account_type: str, days_ahead: int) -> List[Dict[str, Any]]:
        """
        Возвращает тестовые события (fallback).
        
        Args:
            account_type: Тип аккаунта
            days_ahead: Количество дней вперед
            
        Returns:
            Список тестовых событий
        """
        self.logger.info(f"📅 Используются тестовые события для {account_type}")
        
        if account_type == 'personal':
            return [
                {
                    "id": "personal_test_1",
                    "title": "Тестовая встреча",
                    "start": "2025-08-29T15:00:00Z",
                    "end": "2025-08-29T16:00:00Z",
                    "attendees": ["test@example.com"],
                    "attendees_count": 1,
                    "description": "Тестовая встреча для проверки системы",
                    "location": "Онлайн",
                    "source": "sample_data"
                }
            ]
        elif account_type == 'work':
            return [
                {
                    "id": "work_test_1",
                    "title": "Рабочая встреча",
                    "start": "2025-08-29T10:00:00Z",
                    "end": "2025-08-29T11:00:00Z",
                    "attendees": ["colleague@company.com"],
                    "attendees_count": 1,
                    "description": "Рабочая встреча для проверки системы",
                    "location": "Офис",
                    "source": "sample_data"
                }
            ]
        else:
            return []

    def process(self, account_type: str = "personal") -> Dict[str, Any]:
        """
        Основной метод обработки (реализация абстрактного метода).
        
        Args:
            account_type: Тип аккаунта
            
        Returns:
            Результат обработки календаря
        """
        try:
            events = self.get_calendar_events(account_type)
            return {
                "status": "success",
                "events_count": len(events),
                "events": events,
                "message": f"Получено {len(events)} событий из календаря"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "events_count": 0,
                "events": []
            }
