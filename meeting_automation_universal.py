#!/usr/bin/env python3
"""
Универсальный скрипт для автоматизации встреч
Поддерживает различные действия: calendar, drive, media, transcribe, notion, all
ОБНОВЛЕНО: Использует новые модульные handlers вместо устаревших функций
"""

import os
import sys
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import subprocess
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from config_manager import ConfigManager
    from handlers.notion_handler import NotionHandler
    from handlers.account_handler import AccountHandler
    from handlers.media_handler import MediaHandler
    from handlers.transcription_handler import TranscriptionHandler
    from handlers.summary_handler import SummaryHandler
    from telegram_api import TelegramAPI
    NEW_HANDLERS_AVAILABLE = True
    print("✅ Новые модульные обработчики загружены")
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)

def setup_logging():
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler(
                "logs/meeting_automation_universal.log",
                maxBytes=int(os.getenv("LOG_MAX_SIZE_MB", "100")) * 1024 * 1024,
                backupCount=int(os.getenv("LOG_BACKUP_COUNT", "5")),
                encoding="utf-8"
            )
        ]
    )
    return logging.getLogger(__name__)

def load_environment():
    """Загрузка переменных окружения."""
    try:
        # Загружаем конфигурацию
        config_manager = ConfigManager()
        return config_manager
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return None

def process_account(config_manager: ConfigManager, account_type: str, logger: logging.Logger = None):
    """Обработка аккаунта (календарь и диск) через новые handlers."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"📅 Обработка аккаунта: {account_type}")
    
    try:
        # Создаем AccountHandler для обработки аккаунта
        account_handler = AccountHandler(config_manager, logger=logger)
        
        if account_type == 'personal':
            if config_manager.is_personal_enabled():
                logger.info("👤 Обрабатываю личный аккаунт")
                result = account_handler.process_account('personal')
                return result
            else:
                logger.warning("⚠️ Личный аккаунт отключен")
                return {"status": "skipped", "message": "Personal account disabled"}
        
        elif account_type == 'work':
            if config_manager.is_work_enabled():
                logger.info("🏢 Обрабатываю рабочий аккаунт")
                result = account_handler.process_account('work')
                return result
            else:
                logger.warning("⚠️ Рабочий аккаунт отключен")
                return {"status": "skipped", "message": "Work account disabled"}
        
        elif account_type == 'both':
            logger.info("🔄 Обрабатываю оба аккаунта")
            result = account_handler.process_both_accounts()
            return result
        
        else:
            logger.error(f"❌ Неизвестный тип аккаунта: {account_type}")
            return {"status": "error", "message": f"Unknown account type: {account_type}"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка обработки аккаунта {account_type}: {e}")
        return {"status": "error", "message": str(e)}

def process_media(config_manager: ConfigManager, quality: str = 'medium', logger: logging.Logger = None):
    """Обработка медиа файлов через MediaHandler."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎬 Запуск обработки медиа файлов...")
    
    try:
        # Создаем MediaHandler для обработки медиа
        media_handler = MediaHandler(config_manager, logger=logger)
        
        # Обрабатываем медиа файлы
        result = media_handler.process()
        
        logger.info("✅ Обработка медиа завершена")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return {"status": "error", "message": str(e)}

def process_transcription(config_manager: ConfigManager, account_type: str, file_path: str = None, logger: logging.Logger = None):
    """Обработка транскрипции через TranscriptionHandler."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎤 Запуск транскрипции аудио...")
    
    try:
        # Создаем TranscriptionHandler для транскрипции
        transcription_handler = TranscriptionHandler(config_manager, logger=logger)
        
        if file_path:
            # Транскрибируем конкретный файл
            logger.info(f"🎵 Транскрибирую файл: {file_path}")
            result = transcription_handler.process_folder_files(file_path, account_type)
            return result
        else:
            # Транскрибируем все MP3 файлы в папках аккаунтов
            logger.info(f"🎵 Транскрибирую все MP3 файлы для аккаунта: {account_type}")
            result = transcription_handler.process_with_accounts(account_type)
            return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрипции: {e}")
        return {"status": "error", "message": str(e)}

def process_notion_sync(config_manager: ConfigManager, account_type: str, logger: logging.Logger = None):
    """Синхронизация с Notion через NotionHandler."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("📝 Запуск синхронизации с Notion...")
    
    try:
        # Создаем NotionHandler для синхронизации
        notion_handler = NotionHandler(config_manager, logger=logger)
        
        # Синхронизируем с Notion
        result = notion_handler.process()
        
        logger.info("✅ Синхронизация с Notion завершена")
        return result
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
        return {"status": "error", "message": str(e)}

def process_notification(message: str, notification_type: str = "info", logger: logging.Logger = None):
    """Отправка уведомлений в Telegram через TelegramAPI."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("📱 Запуск отправки уведомления...")
    
    try:
        # Получаем настройки Telegram
        config_manager = ConfigManager()
        telegram_config = config_manager.get_telegram_config()
        
        if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
            logger.error("❌ Telegram не настроен")
            return {"status": "error", "message": "Telegram not configured"}
        
        # Инициализируем Telegram API
        telegram_api = TelegramAPI(telegram_config)
        
        # Отправляем сообщение с правильным parse_mode
        if notification_type == "detailed":
            # Для детальных отчетов используем HTML
            success = telegram_api.send_message(message, parse_mode="HTML")
        else:
            # Для обычных уведомлений используем HTML (так как у нас есть разметка)
            success = telegram_api.send_message(message, parse_mode="HTML")
        
        if success:
            logger.info("✅ Уведомление отправлено успешно")
            return {"status": "success", "message": "Notification sent successfully"}
        else:
            logger.error("❌ Не удалось отправить уведомление")
            return {"status": "error", "message": "Failed to send notification"}
            
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}")
        return {"status": "error", "message": str(e)}

def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Универсальный скрипт автоматизации встреч (ОБНОВЛЕНО)')
    parser.add_argument('action', choices=['calendar', 'drive', 'media', 'transcribe', 'notion', 'all', 'notify'],
                       help='Действие для выполнения')
    parser.add_argument('--account', choices=['personal', 'work', 'both'], default='both',
                       help='Тип аккаунта для обработки')
    parser.add_argument('--file', help='Путь к конкретному файлу для обработки')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество обработки медиа')
    parser.add_argument('--message', help='Сообщение для команды notify')
    parser.add_argument('--notification_type', choices=['info', 'detailed'], default='info',
                       help='Тип уведомления для команды notify')
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    logger = setup_logging()
    logger.info(f"🚀 Запуск {args.action} для аккаунта: {args.account} (ОБНОВЛЕНО)")
    
    # Загружаем конфигурацию
    config_manager = load_environment()
    if not config_manager:
        logger.error("❌ Не удалось загрузить конфигурацию")
        sys.exit(1)
    
    try:
        if args.action == 'calendar':
            result = process_account(config_manager, args.account, logger)
        elif args.action == 'drive':
            result = process_account(config_manager, args.account, logger)
        elif args.action == 'media':
            result = process_media(config_manager, args.quality, logger)
        elif args.action == 'transcribe':
            result = process_transcription(config_manager, args.account, args.file, logger)
        elif args.action == 'notion':
            result = process_notion_sync(config_manager, args.account, logger)
        elif args.action == 'notify':
            if not args.message:
                logger.error("❌ Для команды notify необходимо указать --message")
                return 1
            
            result = process_notification(args.message, args.notification_type, logger)
        elif args.action == 'all':
            logger.info("🚀 Запуск всех процессов...")
            results = {}
            results['calendar'] = process_account(config_manager, args.account, logger)
            results['media'] = process_media(config_manager, args.quality, logger)
            results['transcribe'] = process_transcription(config_manager, args.account, args.file, logger)
            results['notion'] = process_notion_sync(config_manager, args.account, logger)
            result = {"status": "success", "message": "All actions completed", "results": results}
        
        logger.info(f"✅ {args.action} завершен: {result}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения {args.action}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
