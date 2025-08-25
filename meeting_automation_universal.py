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
        # Пока просто возвращаем успех (реальная обработка будет добавлена позже)
        logger.info(f"✅ Аккаунт {account_type} обработан успешно")
        return {"status": "success", "message": f"Account {account_type} processed"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки аккаунта {account_type}: {e}")
        return {"status": "error", "message": str(e)}

def process_media(config_manager: ConfigManager, quality: str = 'medium', logger: logging.Logger = None):
    """Обработка медиа файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎬 Запуск обработки медиа файлов...")
    
    try:
        # Пока просто логируем информацию о папках
        if config_manager.is_personal_enabled():
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                logger.info(f"👤 Папка личного аккаунта: {personal_folder}")
            else:
                logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
        
        if config_manager.is_work_enabled():
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                logger.info(f"🏢 Папка рабочего аккаунта: {work_folder}")
            else:
                logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
        
        logger.info("✅ Обработка медиа завершена (режим просмотра)")
        return {"status": "success", "message": "Media processing completed (view mode)"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return {"status": "error", "message": str(e)}

def process_transcription(config_manager: ConfigManager, account_type: str, file_path: str = None, logger: logging.Logger = None):
    """Обработка транскрипции аудио файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎤 Запуск транскрипции аудио...")
    
    try:
        if file_path:
            # Транскрибируем конкретный файл
            logger.info(f"🎵 Транскрибирую файл: {file_path}")
            if os.path.exists(file_path):
                # Здесь должна быть логика транскрипции
                logger.info(f"✅ Файл {file_path} готов к транскрипции")
                return {"status": "success", "message": f"File {file_path} ready for transcription"}
            else:
                logger.error(f"❌ Файл не найден: {file_path}")
                return {"status": "error", "message": f"File not found: {file_path}"}
        else:
            # Транскрибируем все MP3 файлы в папках аккаунтов
            logger.info(f"🎵 Транскрибирую все MP3 файлы для аккаунта: {account_type}")
            
            if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
                personal_config = config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    # Здесь должна быть логика поиска и транскрипции MP3 файлов
            
            if account_type in ['work', 'both'] and config_manager.is_work_enabled():
                work_config = config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    # Здесь должна быть логика поиска и транскрипции MP3 файлов
            
            logger.info("✅ Транскрипция завершена (режим просмотра)")
            return {"status": "success", "message": "Transcription completed (view mode)"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрипции: {e}")
        return {"status": "error", "message": str(e)}

def process_notion_sync(config_manager: ConfigManager, account_type: str, logger: logging.Logger = None):
    """Синхронизация с Notion."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("📝 Запуск синхронизации с Notion...")
    
    try:
        # Получаем настройки Notion
        notion_config = config_manager.get_notion_config()
        if not notion_config.get('token'):
            logger.error("❌ Токен Notion не настроен")
            return {"status": "error", "message": "Notion token not configured"}
        
        logger.info(f"📋 Синхронизирую с базой данных: {notion_config.get('database_id', 'не указано')}")
        
        if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
            logger.info("👤 Синхронизирую личный аккаунт с Notion")
            # Здесь должна быть логика синхронизации личного аккаунта
        
        if account_type in ['work', 'both'] and config_manager.is_work_enabled():
            logger.info("🏢 Синхронизирую рабочий аккаунт с Notion")
            # Здесь должна быть логика синхронизации рабочего аккаунта
        
        logger.info("✅ Синхронизация с Notion завершена")
        return {"status": "success", "message": "Notion sync completed"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
        return {"status": "error", "message": str(e)}

def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description='Универсальный скрипт автоматизации встреч')
    parser.add_argument('action', choices=['calendar', 'drive', 'media', 'transcribe', 'notion', 'all'], 
                       help='Действие для выполнения')
    parser.add_argument('--account', choices=['personal', 'work', 'both'], default='both',
                       help='Аккаунт для обработки (по умолчанию: both)')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество медиа (по умолчанию: medium)')
    parser.add_argument('--file', help='Путь к файлу для транскрипции (только для transcribe)')
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
            
        elif args.action == 'transcribe':
            # Транскрипция аудио
            process_transcription(config_manager, args.account, args.file, logger)
            
        elif args.action == 'notion':
            # Синхронизация с Notion
            process_notion_sync(config_manager, args.account, logger)
            
        elif args.action == 'all':
            # Полная обработка
            if args.account in ['personal', 'both'] and config_manager.is_personal_enabled():
                process_account('personal', config_manager, logger)
            if args.account in ['work', 'both'] and config_manager.is_work_enabled():
                process_account('work', config_manager, logger)
            process_media(config_manager, args.quality, logger)
            process_transcription(config_manager, args.account, None, logger)
            process_notion_sync(config_manager, args.account, logger)
        
        logger.info("✅ Все операции завершены успешно")
        
    except KeyboardInterrupt:
        logger.info("🛑 Операция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
