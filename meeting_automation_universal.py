#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Универсальный скрипт автоматизации встреч
Работает с единой конфигурацией .env для личного и рабочего аккаунтов
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from dotenv import load_dotenv

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent))

from src.config_manager import ConfigManager
from src.calendar_processor import CalendarProcessor
from src.drive_processor import DriveProcessor
from src.media_processor import MediaProcessor
from src.notion_processor import NotionProcessor

def setup_logging():
    """Настройка логирования."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/universal_automation.log')
        ]
    )
    return logging.getLogger(__name__)

def load_environment():
    """Загрузка переменных окружения."""
    logger = logging.getLogger(__name__)
    
    # Загружаем .env файл
    if os.path.exists('.env'):
        load_dotenv('.env')
        logger.info("✅ Загружен основной конфиг: .env")
    else:
        logger.error("❌ Файл .env не найден")
        return None
    
    # Инициализируем ConfigManager
    try:
        config_manager = ConfigManager('.env')
        logger.info("✅ ConfigManager инициализирован")
        return config_manager
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации ConfigManager: {e}")
        return None

def process_account(account_type: str, config_manager: ConfigManager, logger: logging.Logger):
    """Обработка указанного аккаунта."""
    if account_type == 'personal':
        if not config_manager.is_personal_enabled():
            logger.info("⏭️ Личный аккаунт отключен в конфигурации")
            return {"status": "skipped", "message": "Account disabled"}
        
        config = config_manager.get_personal_config()
        logger.info("👤 Обрабатываю личный аккаунт...")
        
    elif account_type == 'work':
        if not config_manager.is_work_enabled():
            logger.info("⏭️ Рабочий аккаунт отключен в конфигурации")
            return {"status": "skipped", "message": "Account disabled"}
        
        config = config_manager.get_work_config()
        logger.info("🏢 Обрабатываю рабочий аккаунт...")
        
    else:
        logger.error(f"❌ Неизвестный тип аккаунта: {account_type}")
        return {"status": "error", "message": "Unknown account type"}
    
    try:
        # Обработка календаря
        calendar_processor = CalendarProcessor(config_manager, account_type)
        calendar_result = calendar_processor.process_calendar()
        logger.info(f"📅 Календарь обработан: {calendar_result}")
        
        # Обработка Google Drive
        drive_processor = DriveProcessor(config_manager, account_type)
        drive_result = drive_processor.process_drive()
        logger.info(f"💾 Google Drive обработан: {drive_result}")
        
        # Обработка Notion
        if config.get('notion_token') and config.get('notion_database_id'):
            notion_processor = NotionProcessor(config_manager, account_type)
            notion_result = notion_processor.process_notion()
            logger.info(f"📝 Notion обработан: {notion_result}")
        else:
            logger.info("⏭️ Notion пропущен (токен или база данных не указаны)")
        
        return {"status": "success", "calendar": calendar_result, "drive": drive_result}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки аккаунта {account_type}: {e}")
        return {"status": "error", "message": str(e)}

def process_media(config_manager: ConfigManager, quality: str = 'medium', logger: logging.Logger = None):
    """Обработка медиа файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎬 Запуск обработки медиа файлов...")
    
    try:
        media_processor = MediaProcessor(config_manager)
        
        # Обрабатываем медиа для личного аккаунта
        if config_manager.is_personal_enabled():
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                logger.info(f"👤 Обрабатываю медиа для личного аккаунта: {personal_folder}")
                personal_result = media_processor.process_folder(personal_folder, quality)
                logger.info(f"✅ Личный аккаунт: {personal_result}")
            else:
                logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
        
        # Обрабатываем медиа для рабочего аккаунта
        if config_manager.is_work_enabled():
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                logger.info(f"🏢 Обрабатываю медиа для рабочего аккаунта: {work_folder}")
                work_result = media_processor.process_folder(work_folder, quality)
                logger.info(f"✅ Рабочий аккаунт: {work_result}")
            else:
                logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
        
        logger.info("✅ Обработка медиа завершена")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return {"status": "error", "message": str(e)}

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Универсальный скрипт автоматизации встреч')
    parser.add_argument('action', choices=['calendar', 'drive', 'media', 'all'], 
                       help='Действие для выполнения')
    parser.add_argument('--account', choices=['personal', 'work', 'both'], default='both',
                       help='Аккаунт для обработки (по умолчанию: both)')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество медиа (по умолчанию: medium)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Подробный вывод')
    
    args = parser.parse_args()
    
    # Настройка логирования
    logger = setup_logging()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    logger.info("🚀 Запуск универсального скрипта автоматизации встреч")
    
    # Загрузка конфигурации
    config_manager = load_environment()
    if not config_manager:
        logger.error("❌ Не удалось загрузить конфигурацию")
        sys.exit(1)
    
    # Проверка конфигурации
    if not config_manager.validate_config():
        logger.warning("⚠️ Конфигурация содержит ошибки")
    
    # Вывод информации о конфигурации
    logger.info("📋 Конфигурация:")
    logger.info(f"   👤 Личный аккаунт: {'включен' if config_manager.is_personal_enabled() else 'отключен'}")
    logger.info(f"   🏢 Рабочий аккаунт: {'включен' if config_manager.is_work_enabled() else 'отключен'}")
    
    try:
        if args.action == 'calendar':
            # Обработка календарей
            if args.account in ['personal', 'both'] and config_manager.is_personal_enabled():
                process_account('personal', config_manager, logger)
            if args.account in ['work', 'both'] and config_manager.is_work_enabled():
                process_account('work', config_manager, logger)
                
        elif args.action == 'drive':
            # Обработка Google Drive
            if args.account in ['personal', 'both'] and config_manager.is_personal_enabled():
                process_account('personal', config_manager, logger)
            if args.account in ['work', 'both'] and config_manager.is_work_enabled():
                process_account('work', config_manager, logger)
                
        elif args.action == 'media':
            # Обработка медиа
            process_media(config_manager, args.quality, logger)
            
        elif args.action == 'all':
            # Полная обработка
            if args.account in ['personal', 'both'] and config_manager.is_personal_enabled():
                process_account('personal', config_manager, logger)
            if args.account in ['work', 'both'] and config_manager.is_work_enabled():
                process_account('work', config_manager, logger)
            process_media(config_manager, args.quality, logger)
        
        logger.info("✅ Все операции завершены успешно")
        
    except KeyboardInterrupt:
        logger.info("🛑 Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
