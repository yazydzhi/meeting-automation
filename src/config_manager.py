#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Менеджер конфигурации для альтернативных провайдеров
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class ConfigManager:
    """Менеджер конфигурации для альтернативных провайдеров."""
    
    def __init__(self, env_file: str = '.env'):
        self.env_file = env_file
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Загрузить конфигурацию из .env файла."""
        logger.info(f"🔧 Загружаю конфигурацию из файла: {self.env_file}")
        
        # Пробуем load_dotenv
        load_dotenv(self.env_file)
        
        # Альтернативный способ загрузки переменных
        if os.path.exists(self.env_file):
            with open(self.env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Убираем кавычки если есть
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        os.environ[key] = value
                        logger.info(f"🔧 Загружена переменная: {key}={value}")
        
        # Проверяем загруженные переменные
        transcription_method = os.getenv('TRANSCRIPTION_METHOD', 'NOT_FOUND')
        logger.info(f"🔧 TRANSCRIPTION_METHOD: {transcription_method}")
        
        # Настройки календаря
        self.config['calendar'] = {
            'provider_type': os.getenv('CALENDAR_PROVIDER', 'google_api'),
            'google_api': {
                'credentials_path': os.getenv('GOOGLE_CALENDAR_CREDENTIALS', ''),
                'calendar_id': os.getenv('PERSONAL_CALENDAR_ID', '')
            },
            'notion': {
                'notion_token': os.getenv('NOTION_TOKEN', ''),
                'database_id': os.getenv('NOTION_CALENDAR_DATABASE_ID', '')
            },
            'web_ical': {
                'calendar_url': os.getenv('ICAL_CALENDAR_URL', '')
            },
            'web_rss': {
                'calendar_url': os.getenv('RSS_CALENDAR_URL', '')
            },
            'local_ics': {
                'calendar_file': os.getenv('LOCAL_ICS_FILE', '')
            },
            'local_json': {
                'calendar_file': os.getenv('LOCAL_JSON_FILE', '')
            }
        }
        
        # Настройки Google Drive
        self.config['drive'] = {
            'provider_type': os.getenv('DRIVE_PROVIDER', 'google_api'),
            'google_api': {
                'credentials_path': os.getenv('GOOGLE_DRIVE_CREDENTIALS', '')
            },
            'local': {
                'root_path': os.getenv('LOCAL_DRIVE_ROOT', 'data/local_drive')
            },
            'google_desktop': {
                'drive_path': os.getenv('GOOGLE_DRIVE_DESKTOP_PATH', '')
            }
        }
        
        # Общие настройки
        self.config['general'] = {
            'timezone': os.getenv('TIMEZONE', 'Europe/Moscow'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO')
        }
        
        # Настройки Whisper и транскрипции
        self.config['whisper'] = {
            'transcription_method': os.getenv('TRANSCRIPTION_METHOD', 'openai'),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'whisper_model': os.getenv('WHISPER_MODEL', 'whisper-1'),
            'whisper_model_local': os.getenv('WHISPER_MODEL_LOCAL', 'base'),
            'whisper_language': os.getenv('WHISPER_LANGUAGE', 'ru'),
            'whisper_task': os.getenv('WHISPER_TASK', 'transcribe'),
            'remove_echo': os.getenv('REMOVE_ECHO', 'true').lower() == 'true',
            'audio_normalize': os.getenv('AUDIO_NORMALIZE', 'true').lower() == 'true',
            'temp_audio_root': os.getenv('TEMP_AUDIO_ROOT', 'data/temp_audio')
        }
        
        logger.info(f"🔧 Настройки Whisper: {self.config['whisper']}")
        logger.info("Конфигурация загружена")
    
    def get_calendar_config(self) -> Dict[str, Any]:
        """Получить конфигурацию календаря."""
        return self.config['calendar']
    
    def get_drive_config(self) -> Dict[str, Any]:
        """Получить конфигурацию Google Drive."""
        return self.config['drive']
    
    def get_calendar_provider_type(self) -> str:
        """Получить тип провайдера календаря."""
        return self.config['calendar']['provider_type']
    
    def get_drive_provider_type(self) -> str:
        """Получить тип провайдера Google Drive."""
        return self.config['drive']['provider_type']
    
    def get_calendar_provider_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для текущего провайдера календаря."""
        provider_type = self.get_calendar_provider_type()
        return self.config['calendar'].get(provider_type, {})
    
    def get_drive_provider_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для текущего провайдера Google Drive."""
        provider_type = self.get_drive_provider_type()
        return self.config['drive'].get(provider_type, {})
    
    def validate_config(self) -> bool:
        """Проверить корректность конфигурации."""
        errors = []
        
        # Проверяем календарь
        calendar_config = self.get_calendar_config()
        provider_type = calendar_config['provider_type']
        provider_config = calendar_config.get(provider_type, {})
        
        if provider_type == 'google_api':
            if not provider_config.get('credentials_path'):
                errors.append("GOOGLE_CALENDAR_CREDENTIALS не указан для google_api")
            if not provider_config.get('calendar_id'):
                errors.append("PERSONAL_CALENDAR_ID не указан для google_api")
        elif provider_type == 'notion':
            if not provider_config.get('notion_token'):
                errors.append("NOTION_TOKEN не указан для notion")
            if not provider_config.get('database_id'):
                errors.append("NOTION_CALENDAR_DATABASE_ID не указан для notion")
        elif provider_type == 'web_ical':
            if not provider_config.get('calendar_url'):
                errors.append("ICAL_CALENDAR_URL не указан для web_ical")
        elif provider_type == 'web_rss':
            if not provider_config.get('calendar_url'):
                errors.append("RSS_CALENDAR_URL не указан для web_rss")
        elif provider_type == 'local_ics':
            if not provider_config.get('calendar_file'):
                errors.append("LOCAL_ICS_FILE не указан для local_ics")
        elif provider_type == 'local_json':
            if not provider_config.get('calendar_file'):
                errors.append("LOCAL_JSON_FILE не указан для local_json")
        
        # Проверяем Google Drive
        drive_config = self.get_drive_config()
        drive_provider_type = drive_config['provider_type']
        drive_provider_config = drive_config.get(drive_provider_type, {})
        
        if drive_provider_type == 'google_api':
            if not drive_provider_config.get('credentials_path'):
                errors.append("GOOGLE_DRIVE_CREDENTIALS не указан для google_api")
        elif drive_provider_type == 'google_desktop':
            if not drive_provider_config.get('drive_path'):
                errors.append("GOOGLE_DRIVE_DESKTOP_PATH не указан для google_desktop")
            elif not os.path.exists(drive_provider_config['drive_path']):
                errors.append(f"Путь Google Drive не найден: {drive_provider_config['drive_path']}")
        
        if errors:
            for error in errors:
                logger.error(f"Ошибка конфигурации: {error}")
            return False
        
        logger.info("Конфигурация корректна")
        return True
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получить значение конфигурации по ключу."""
        # Сначала ищем в переменных окружения
        value = os.getenv(key)
        if value is not None:
            return value
        
        # Затем ищем в структуре конфигурации
        if key == 'LOG_LEVEL':
            return self.config['general'].get('log_level', default)
        elif key == 'TIMEZONE':
            return self.config['general'].get('timezone', default)
        
        return default
    
    def get_config_summary(self) -> str:
        """Получить краткое описание конфигурации."""
        summary = "📋 Конфигурация системы:\n\n"
        
        # Календарь
        calendar_type = self.get_calendar_provider_type()
        summary += f"📅 Календарь: {calendar_type}\n"
        
        if calendar_type == 'google_api':
            config = self.config['calendar']['google_api']
            summary += f"   - Учетные данные: {config['credentials_path']}\n"
            summary += f"   - ID календаря: {config['calendar_id']}\n"
        elif calendar_type == 'notion':
            config = self.config['calendar']['notion']
            summary += f"   - База данных: {config['database_id']}\n"
        elif calendar_type in ['web_ical', 'web_rss']:
            config = self.config['calendar'][calendar_type]
            summary += f"   - URL: {config['calendar_url']}\n"
        elif calendar_type in ['local_ics', 'local_json']:
            config = self.config['calendar'][calendar_type]
            summary += f"   - Файл: {config['calendar_file']}\n"
        
        # Google Drive
        drive_type = self.get_drive_provider_type()
        summary += f"\n💾 Google Drive: {drive_type}\n"
        
        if drive_type == 'google_api':
            config = self.config['drive']['google_api']
            summary += f"   - Учетные данные: {config['credentials_path']}\n"
        elif drive_type == 'local':
            config = self.config['drive']['local']
            summary += f"   - Локальная папка: {config['root_path']}\n"
        elif drive_type == 'google_desktop':
            config = self.config['drive']['google_desktop']
            summary += f"   - Путь: {config['drive_path']}\n"
        
        return summary
    
    def update_config(self, section: str, key: str, value: str):
        """Обновить значение конфигурации."""
        if section in self.config and key in self.config[section]:
            self.config[section][key] = value
            logger.info(f"Конфигурация обновлена: {section}.{key} = {value}")
        else:
            logger.error(f"Неизвестный параметр конфигурации: {section}.{key}")
    
    def save_to_env(self):
        """Сохранить конфигурацию в .env файл."""
        try:
            env_lines = []
            
            # Читаем существующий .env файл
            if os.path.exists(self.env_file):
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    existing_lines = f.readlines()
                
                # Фильтруем строки, которые мы не обновляем
                for line in existing_lines:
                    if not any(key in line for key in [
                        'CALENDAR_PROVIDER', 'DRIVE_PROVIDER',
                        'GOOGLE_CALENDAR_CREDENTIALS', 'PERSONAL_CALENDAR_ID',
                        'NOTION_CALENDAR_DATABASE_ID', 'ICAL_CALENDAR_URL',
                        'RSS_CALENDAR_URL', 'LOCAL_ICS_FILE', 'LOCAL_JSON_FILE',
                        'GOOGLE_DRIVE_CREDENTIALS', 'LOCAL_DRIVE_ROOT',
                        'GOOGLE_DRIVE_DESKTOP_PATH'
                    ]):
                        env_lines.append(line)
            
            # Добавляем новые настройки
            env_lines.append(f"\n# Альтернативные провайдеры\n")
            env_lines.append(f"CALENDAR_PROVIDER={self.config['calendar']['provider_type']}\n")
            env_lines.append(f"DRIVE_PROVIDER={self.config['drive']['provider_type']}\n")
            
            # Настройки календаря
            calendar_type = self.config['calendar']['provider_type']
            if calendar_type == 'google_api':
                config = self.config['calendar']['google_api']
                env_lines.append(f"GOOGLE_CALENDAR_CREDENTIALS={config['credentials_path']}\n")
                env_lines.append(f"PERSONAL_CALENDAR_ID={config['calendar_id']}\n")
            elif calendar_type == 'notion':
                config = self.config['calendar']['notion']
                env_lines.append(f"NOTION_CALENDAR_DATABASE_ID={config['database_id']}\n")
            elif calendar_type == 'web_ical':
                config = self.config['calendar']['web_ical']
                env_lines.append(f"ICAL_CALENDAR_URL={config['calendar_url']}\n")
            elif calendar_type == 'web_rss':
                config = self.config['calendar']['web_rss']
                env_lines.append(f"RSS_CALENDAR_URL={config['calendar_url']}\n")
            elif calendar_type == 'local_ics':
                config = self.config['calendar']['local_ics']
                env_lines.append(f"LOCAL_ICS_FILE={config['calendar_file']}\n")
            elif calendar_type == 'local_json':
                config = self.config['calendar']['local_json']
                env_lines.append(f"LOCAL_JSON_FILE={config['calendar_file']}\n")
            
            # Настройки Google Drive
            drive_type = self.config['drive']['provider_type']
            if drive_type == 'google_api':
                config = self.config['drive']['google_api']
                env_lines.append(f"GOOGLE_DRIVE_CREDENTIALS={config['credentials_path']}\n")
            elif drive_type == 'local':
                config = self.config['drive']['local']
                env_lines.append(f"LOCAL_DRIVE_ROOT={config['root_path']}\n")
            elif drive_type == 'google_desktop':
                config = self.config['drive']['google_desktop']
                env_lines.append(f"GOOGLE_DRIVE_DESKTOP_PATH={config['drive_path']}\n")
            
            # Записываем в .env файл
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(env_lines)
            
            logger.info(f"Конфигурация сохранена в {self.env_file}")
            
        except Exception as e:
            logger.error(f"Ошибка сохранения конфигурации: {e}")

def create_sample_env():
    """Создать пример .env файла с альтернативными провайдерами."""
    sample_env = """# Google API (стандартный способ)
GOOGLE_CREDENTIALS=creds/client_secret.json
PERSONAL_CALENDAR_ID=your_calendar_id
PERSONAL_DRIVE_PARENT_ID=your_drive_folder_id

# Notion
NOTION_TOKEN=your_notion_token
NOTION_DATABASE_ID=your_database_id

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Медиа обработка
MEDIA_OUTPUT_FORMAT=mp3
MEDIA_QUALITY=medium
MEDIA_SYNC_ROOT=data/synced
MEDIA_CLEANUP_DAYS=30

# Компрессия видео
VIDEO_COMPRESSION=true
VIDEO_QUALITY=medium
VIDEO_CODEC=h264

# Временная зона
TIMEZONE=Europe/Moscow

# ========================================
# АЛЬТЕРНАТИВНЫЕ ПРОВАЙДЕРЫ
# ========================================

# Тип провайдера календаря (google_api, notion, web_ical, web_rss, local_ics, local_json)
CALENDAR_PROVIDER=google_api

# Тип провайдера Google Drive (google_api, local, google_desktop)
DRIVE_PROVIDER=google_api

# ========================================
# НАСТРОЙКИ ДЛЯ РАЗНЫХ ПРОВАЙДЕРОВ
# ========================================

# Notion календарь
NOTION_CALENDAR_DATABASE_ID=your_calendar_database_id

# Веб-календари (iCal, RSS)
ICAL_CALENDAR_URL=https://calendar.google.com/calendar/ical/your_calendar_id/basic.ics
RSS_CALENDAR_URL=https://calendar.google.com/calendar/feeds/your_calendar_id/public/basic

# Локальные файлы календаря
LOCAL_ICS_FILE=data/calendar/events.ics
LOCAL_JSON_FILE=data/calendar/events.json

# Локальная файловая система
LOCAL_DRIVE_ROOT=data/local_drive

# Google Drive для Desktop
GOOGLE_DRIVE_DESKTOP_PATH=/Users/username/Google Drive
"""
    
    with open('.env.sample', 'w', encoding='utf-8') as f:
        f.write(sample_env)
    
    logger.info("Создан пример .env файла: .env.sample")

if __name__ == "__main__":
    # Создаем пример конфигурации
    create_sample_env()
    
    # Тестируем загрузку конфигурации
    config = ConfigManager()
    print(config.get_config_summary())
    
    if config.validate_config():
        print("✅ Конфигурация корректна")
    else:
        print("❌ Конфигурация содержит ошибки")
