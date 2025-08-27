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
        account_type = os.getenv('ACCOUNT_TYPE', 'both')
        logger.info(f"🔧 ACCOUNT_TYPE: {account_type}")
        
        # Общие настройки Telegram и Notion
        self.config['telegram'] = {
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
        }
        
        self.config['notion'] = {
            'token': os.getenv('NOTION_TOKEN', ''),
            'database_id': os.getenv('NOTION_DATABASE_ID', ''),
            'parent_page_id': os.getenv('NOTION_PARENT_PAGE_ID', ''),
            'db_title': os.getenv('NOTION_DB_TITLE', '')
        }
        
        # Настройки аккаунтов
        self.config['accounts'] = {
            'type': account_type,
            'personal': {
                'enabled': account_type in ['personal', 'both'],
                'google_credentials': os.getenv('PERSONAL_GOOGLE_CREDENTIALS', ''),
                'calendar_id': os.getenv('PERSONAL_CALENDAR_ID', ''),
                'drive_parent_id': os.getenv('PERSONAL_DRIVE_PARENT_ID', ''),
                'calendar_provider': os.getenv('PERSONAL_CALENDAR_PROVIDER', 'web_ical'),
                'ical_calendar_url': os.getenv('PERSONAL_ICAL_CALENDAR_URL', ''),
                'drive_provider': os.getenv('PERSONAL_DRIVE_PROVIDER', 'local'),
                'local_drive_root': os.getenv('PERSONAL_LOCAL_DRIVE_ROOT', '')
            },
            'work': {
                'enabled': account_type in ['work', 'both'],
                'google_credentials': os.getenv('WORK_GOOGLE_CREDENTIALS', ''),
                'calendar_id': os.getenv('WORK_CALENDAR_ID', ''),
                'drive_parent_id': os.getenv('WORK_DRIVE_PARENT_ID', ''),
                'calendar_provider': os.getenv('WORK_CALENDAR_PROVIDER', 'web_ical'),
                'ical_calendar_url': os.getenv('WORK_ICAL_CALENDAR_URL', ''),
                'drive_provider': os.getenv('WORK_DRIVE_PROVIDER', 'local'),
                'local_drive_root': os.getenv('WORK_LOCAL_DRIVE_ROOT', '')
            }
        }
        
        # Общие настройки
        self.config['general'] = {
            'timezone': os.getenv('TIMEZONE', 'Europe/Moscow'),
            'log_level': os.getenv('LOG_LEVEL', 'INFO'),
            'service_check_interval': int(os.getenv('SERVICE_CHECK_INTERVAL', '300')),
            'service_media_interval': int(os.getenv('SERVICE_MEDIA_INTERVAL', '1800')),
            'media_processing_timeout': int(os.getenv('MEDIA_PROCESSING_TIMEOUT', '1800'))
        }
        
        # Настройки медиа обработки
        self.config['media'] = {
            'output_format': os.getenv('MEDIA_OUTPUT_FORMAT', 'mp3'),
            'quality': os.getenv('MEDIA_QUALITY', 'medium'),
            'cleanup_days': int(os.getenv('MEDIA_CLEANUP_DAYS', '30')),
            'video_compression': os.getenv('VIDEO_COMPRESSION', 'true').lower() == 'true',
            'video_quality': os.getenv('VIDEO_QUALITY', 'medium'),
            'video_codec': os.getenv('VIDEO_CODEC', 'h264')
        }
        
        # Настройки Whisper и транскрипции
        self.config['whisper'] = {
            'transcription_method': os.getenv('TRANSCRIPTION_METHOD', 'whisper'),
            'openai_api_key': os.getenv('OPENAI_API_KEY', ''),
            'whisper_model': os.getenv('WHISPER_MODEL', 'whisper-1'),
            'whisper_model_local': os.getenv('WHISPER_MODEL_LOCAL', 'base'),
            'whisper_language': os.getenv('WHISPER_LANGUAGE', 'ru'),
            'whisper_task': os.getenv('WHISPER_TASK', 'transcribe'),
            'remove_echo': os.getenv('REMOVE_ECHO', 'true').lower() == 'true',
            'audio_normalize': os.getenv('AUDIO_NORMALIZE', 'true').lower() == 'true',
            'temp_audio_root': os.getenv('TEMP_AUDIO_ROOT', 'data/temp_audio')
        }
        
        # Настройки OpenAI для анализа
        self.config['openai'] = {
            'api_key': os.getenv('OPENAI_API_KEY', ''),
            'analysis_model': os.getenv('OPENAI_ANALYSIS_MODEL', 'gpt-4o-mini'),
            'analysis_temperature': float(os.getenv('OPENAI_ANALYSIS_TEMPERATURE', '0.3')),
            'analysis_max_tokens': int(os.getenv('OPENAI_ANALYSIS_MAX_TOKENS', '4000'))
        }
        
        # TASK-3: Настройки промптов
        self.config['prompts'] = {
            'transcription': {
                'prompt_custom': os.getenv('TRANSCRIPTION_PROMPT_CUSTOM', ''),
                'temperature': float(os.getenv('TRANSCRIPTION_TEMPERATURE', '0.1')),
                'max_tokens': int(os.getenv('TRANSCRIPTION_MAX_TOKENS', '4000')),
                'model': os.getenv('TRANSCRIPTION_MODEL', 'whisper-1'),
                'language': os.getenv('TRANSCRIPTION_LANGUAGE', 'ru'),
                'include_timestamps': os.getenv('TRANSCRIPTION_INCLUDE_TIMESTAMPS', 'true').lower() == 'true',
                'speaker_detection': os.getenv('TRANSCRIPTION_SPEAKER_DETECTION', 'true').lower() == 'true',
                'quality_notes': os.getenv('TRANSCRIPTION_QUALITY_NOTES', 'true').lower() == 'true'
            },
            'summary': {
                'prompt_custom': os.getenv('SUMMARY_PROMPT_CUSTOM', ''),
                'temperature': float(os.getenv('SUMMARY_TEMPERATURE', '0.3')),
                'max_tokens': int(os.getenv('SUMMARY_MAX_TOKENS', '2000')),
                'model': os.getenv('SUMMARY_MODEL', 'gpt-4o-mini'),
                'style': os.getenv('SUMMARY_STYLE', 'professional'),
                'include_actions': os.getenv('SUMMARY_INCLUDE_ACTIONS', 'true').lower() == 'true',
                'include_deadlines': os.getenv('SUMMARY_INCLUDE_DEADLINES', 'true').lower() == 'true',
                'include_risks': os.getenv('SUMMARY_INCLUDE_RISKS', 'true').lower() == 'true',
                'max_length': os.getenv('SUMMARY_MAX_LENGTH', 'medium')
            },
            'analysis': {
                'prompt_custom': os.getenv('ANALYSIS_PROMPT_CUSTOM', ''),
                'temperature': float(os.getenv('ANALYSIS_TEMPERATURE', '0.2')),
                'max_tokens': int(os.getenv('ANALYSIS_MAX_TOKENS', '4000')),
                'model': os.getenv('ANALYSIS_MODEL', 'gpt-4o-mini'),
                'include_financial': os.getenv('ANALYSIS_INCLUDE_FINANCIAL', 'true').lower() == 'true',
                'include_quotes': os.getenv('ANALYSIS_INCLUDE_QUOTES', 'true').lower() == 'true',
                'include_metrics': os.getenv('ANALYSIS_INCLUDE_METRICS', 'true').lower() == 'true',
                'include_risks': os.getenv('ANALYSIS_INCLUDE_RISKS', 'true').lower() == 'true',
                'output_format': os.getenv('ANALYSIS_OUTPUT_FORMAT', 'json')
            },
            'complex_analysis': {
                'prompt_custom': os.getenv('COMPLEX_ANALYSIS_PROMPT_CUSTOM', ''),
                'temperature': float(os.getenv('COMPLEX_ANALYSIS_TEMPERATURE', '0.4')),
                'max_tokens': int(os.getenv('COMPLEX_ANALYSIS_MAX_TOKENS', '6000')),
                'model': os.getenv('COMPLEX_ANALYSIS_MODEL', 'gpt-4o-mini'),
                'include_trends': os.getenv('COMPLEX_ANALYSIS_INCLUDE_TRENDS', 'true').lower() == 'true',
                'include_progress': os.getenv('COMPLEX_ANALYSIS_INCLUDE_PROGRESS', 'true').lower() == 'true',
                'include_recurring': os.getenv('COMPLEX_ANALYSIS_INCLUDE_RECURRING', 'true').lower() == 'true',
                'include_insights': os.getenv('COMPLEX_ANALYSIS_INCLUDE_INSIGHTS', 'true').lower() == 'true',
                'max_meetings': int(os.getenv('COMPLEX_ANALYSIS_MAX_MEETINGS', '10'))
            },
            'general': {
                'quality_level': os.getenv('PROMPT_QUALITY_LEVEL', 'balanced'),
                'language': os.getenv('PROMPT_LANGUAGE', 'russian'),
                'style': os.getenv('PROMPT_STYLE', 'professional'),
                'output_format': os.getenv('PROMPT_OUTPUT_FORMAT', 'json'),
                'api_timeout': int(os.getenv('PROMPT_API_TIMEOUT', '60')),
                'max_retries': int(os.getenv('PROMPT_MAX_RETRIES', '3')),
                'retry_delay': int(os.getenv('PROMPT_RETRY_DELAY', '5')),
                'logging': os.getenv('PROMPT_LOGGING', 'true').lower() == 'true',
                'debug_save': os.getenv('PROMPT_DEBUG_SAVE', 'false').lower() == 'true',
                'debug_dir': os.getenv('PROMPT_DEBUG_DIR', 'logs/prompts')
            }
        }
        
        logger.info(f"🔧 Настройки аккаунтов: {self.config['accounts']}")
        logger.info(f"🔧 Настройки медиа: {self.config['media']}")
        logger.info(f"🔧 Настройки Whisper: {self.config['whisper']}")
        logger.info(f"🔧 Настройки OpenAI: {self.config['openai']}")
        logger.info(f"🔧 TASK-3: Настройки промптов загружены")
        logger.info("Конфигурация загружена")
    
    def get_accounts_config(self) -> Dict[str, Any]:
        """Получить конфигурацию аккаунтов."""
        return self.config['accounts']
    
    def get_personal_config(self) -> Dict[str, Any]:
        """Получить конфигурацию личного аккаунта."""
        return self.config['accounts']['personal']
    
    def get_work_config(self) -> Dict[str, Any]:
        """Получить конфигурацию рабочего аккаунта."""
        return self.config['accounts']['work']
    
    def is_personal_enabled(self) -> bool:
        """Проверить, включен ли личный аккаунт."""
        return self.config['accounts']['personal']['enabled']
    
    def is_work_enabled(self) -> bool:
        """Проверить, включен ли рабочий аккаунт."""
        return self.config['accounts']['work']['enabled']
    
    def get_media_config(self) -> Dict[str, Any]:
        """Получить конфигурацию медиа обработки."""
        return self.config['media']
    
    def get_general_config(self) -> Dict[str, Any]:
        """Получить общие настройки."""
        return self.config['general']
    
    def get_whisper_config(self) -> Dict[str, Any]:
        """Получить настройки Whisper."""
        return self.config['whisper']
    
    def get_telegram_config(self) -> Dict[str, Any]:
        """Получить общие настройки Telegram."""
        return self.config['telegram']
    

    def get_notion_config(self) -> Dict[str, Any]:
        """Получить общие настройки Notion."""
        return self.config["notion"]

    def get_openai_config(self) -> Dict[str, Any]:
        """Получить настройки OpenAI."""
        return self.config["openai"]
    
    def get_prompts_config(self) -> Dict[str, Any]:
        """Получить настройки промптов."""
        return self.config["prompts"]
    
    def get_prompt_config(self, prompt_type: str) -> Dict[str, Any]:
        """
        Получить настройки для конкретного типа промпта.
        
        Args:
            prompt_type: Тип промпта ('transcription', 'summary', 'analysis', 'complex_analysis')
            
        Returns:
            Настройки промпта
        """
        if prompt_type in self.config["prompts"]:
            return self.config["prompts"][prompt_type]
        else:
            logger.warning(f"⚠️ Неизвестный тип промпта: {prompt_type}")
            return {}
    
    def get_prompt_general_config(self) -> Dict[str, Any]:
        """Получить общие настройки промптов."""
        return self.config["prompts"]["general"]
    def get_calendar_provider_type(self, account_type: str = 'personal') -> str:
        """Получить тип провайдера календаря для указанного аккаунта."""
        if account_type == 'personal':
            return self.config['accounts']['personal']['calendar_provider']
        elif account_type == 'work':
            return self.config['accounts']['work']['calendar_provider']
        return 'web_ical'
    
    def get_drive_provider_type(self, account_type: str = 'personal') -> str:
        """Получить тип провайдера Google Drive для указанного аккаунта."""
        if account_type == 'personal':
            return self.config['accounts']['personal']['drive_provider']
        elif account_type == 'work':
            return self.config['accounts']['work']['drive_provider']
        return 'local'
    
    def get_calendar_provider_config(self, account_type: str = 'personal') -> Dict[str, Any]:
        """Получить конфигурацию для текущего провайдера календаря указанного аккаунта."""
        if account_type == 'personal':
            config = {
                'provider_type': self.config['accounts']['personal']['calendar_provider'],
                'calendar_url': self.config['accounts']['personal']['ical_calendar_url']
            }
            
            # Добавляем timezone для Google Calendar API
            if config['provider_type'] == 'google_api':
                config['credentials_path'] = self.config['accounts']['personal'].get('google_credentials_path', '')
                config['calendar_id'] = self.config['accounts']['personal'].get('google_calendar_id', '')
                config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
            elif config['provider_type'] in ['web_ical', 'web_rss']:
                # Добавляем timezone для web календарей
                config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
            
            return config
        elif account_type == 'work':
            config = {
                'provider_type': self.config['accounts']['work']['calendar_provider'],
                'calendar_url': self.config['accounts']['work']['ical_calendar_url']
            }
            
            # Добавляем timezone для Google Calendar API
            if config['provider_type'] == 'google_api':
                config['credentials_path'] = self.config['accounts']['work'].get('google_credentials_path', '')
                config['calendar_id'] = self.config['accounts']['work'].get('google_calendar_id', '')
                config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
            elif config['provider_type'] in ['web_ical', 'web_rss']:
                # Добавляем timezone для web календарей
                config['timezone'] = self.config['general'].get('timezone', 'Europe/Moscow')
            
            return config
        return {}
    
    def get_drive_provider_config(self, account_type: str = 'personal') -> Dict[str, Any]:
        """Получить конфигурацию для текущего провайдера Google Drive указанного аккаунта."""
        if account_type == 'personal':
            return {
                'provider_type': self.config['accounts']['personal']['drive_provider'],
                'root_path': self.config['accounts']['personal']['local_drive_root']
            }
        elif account_type == 'work':
            return {
                'provider_type': self.config['accounts']['work']['drive_provider'],
                'root_path': self.config['accounts']['work']['local_drive_root']
            }
        return {}
    
    def validate_config(self) -> bool:
        """Проверить корректность конфигурации."""
        errors = []
        
        # Проверяем настройки аккаунтов
        account_type = self.config['accounts']['type']
        logger.info(f"🔧 Проверяю конфигурацию для типа аккаунта: {account_type}")
        
        # Проверяем личный аккаунт
        if self.is_personal_enabled():
            personal_config = self.get_personal_config()
            logger.info("🔧 Проверяю личный аккаунт...")
            
            if personal_config['calendar_provider'] == 'web_ical':
                if not personal_config['ical_calendar_url']:
                    errors.append("PERSONAL_ICAL_CALENDAR_URL не указан для личного аккаунта")
            
            if personal_config['drive_provider'] == 'local':
                if not personal_config['local_drive_root']:
                    errors.append("PERSONAL_LOCAL_DRIVE_ROOT не указан для личного аккаунта")
                elif not os.path.exists(personal_config['local_drive_root']):
                    errors.append(f"Путь личного Google Drive не найден: {personal_config['local_drive_root']}")
        
        # Проверяем рабочий аккаунт
        if self.is_work_enabled():
            work_config = self.get_work_config()
            logger.info("🔧 Проверяю рабочий аккаунт...")
            
            if work_config['calendar_provider'] == 'web_ical':
                if not work_config['ical_calendar_url']:
                    errors.append("WORK_ICAL_CALENDAR_URL не указан для рабочего аккаунта")
            
            if work_config['drive_provider'] == 'local':
                if not work_config['local_drive_root']:
                    errors.append("WORK_LOCAL_DRIVE_ROOT не указан для рабочего аккаунта")
                elif not os.path.exists(work_config['local_drive_root']):
                    errors.append(f"Путь рабочего Google Drive не найден: {work_config['local_drive_root']}")
        
        if errors:
            for error in errors:
                logger.error(f"Ошибка конфигурации: {error}")
            return False
        
        logger.info("✅ Конфигурация корректна")
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
        
        # Тип аккаунта
        account_type = self.config['accounts']['type']
        summary += f"👤 Тип аккаунта: {account_type}\n\n"
        
        # Личный аккаунт
        if self.is_personal_enabled():
            personal_config = self.get_personal_config()
            summary += "👤 Личный аккаунт:\n"
            summary += f"   - Календарь: {personal_config['calendar_provider']}\n"
            if personal_config['calendar_provider'] == 'web_ical':
                summary += f"   - ICAL URL: {personal_config['ical_calendar_url']}\n"
            summary += f"   - Google Drive: {personal_config['drive_provider']}\n"
            if personal_config['drive_provider'] == 'local':
                summary += f"   - Локальная папка: {personal_config['local_drive_root']}\n"
            summary += "\n"
        
        # Рабочий аккаунт
        if self.is_work_enabled():
            work_config = self.get_work_config()
            summary += "🏢 Рабочий аккаунт:\n"
            summary += f"   - Календарь: {work_config['calendar_provider']}\n"
            if work_config['calendar_provider'] == 'web_ical':
                summary += f"   - ICAL URL: {work_config['ical_calendar_url']}\n"
            summary += f"   - Google Drive: {work_config['drive_provider']}\n"
            if work_config['drive_provider'] == 'local':
                summary += f"   - Локальная папка: {work_config['local_drive_root']}\n"
            summary += "\n"
        
        # Медиа обработка
        media_config = self.get_media_config()
        summary += "🎬 Медиа обработка:\n"
        summary += f"   - Формат: {media_config['output_format']}\n"
        summary += f"   - Качество: {media_config['quality']}\n"
        summary += f"   - Сжатие видео: {media_config['video_compression']}\n"
        summary += "\n"
        
        # Telegram
        telegram_config = self.get_telegram_config()
        summary += "📱 Telegram:\n"
        summary += f"   - Bot Token: {'✅ Настроен' if telegram_config['bot_token'] else '❌ Не настроен'}\n"
        summary += f"   - Chat ID: {telegram_config['chat_id']}\n"
        summary += "\n"
        
        # Notion
        notion_config = self.get_notion_config()
        summary += "📝 Notion:\n"
        summary += f"   - Token: {'✅ Настроен' if notion_config['token'] else '❌ Не настроен'}\n"
        summary += f"   - Database ID: {notion_config['database_id']}\n"
        summary += f"   - DB Title: {notion_config['db_title']}\n"
        summary += "\n"
        
        # Whisper
        whisper_config = self.get_whisper_config()
        summary += "🎤 Whisper:\n"
        summary += f"   - Метод: {whisper_config['transcription_method']}\n"
        summary += f"   - Модель: {whisper_config['whisper_model']}\n"
        summary += f"   - Язык: {whisper_config['whisper_language']}\n"
        
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
