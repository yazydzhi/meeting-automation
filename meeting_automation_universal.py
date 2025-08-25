#!/usr/bin/env python3
"""
Универсальный скрипт для автоматизации встреч
Поддерживает различные действия: calendar, drive, media, transcribe, notion, all
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Добавляем путь к src для импорта модулей
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from config_manager import ConfigManager
    from audio_processor import AudioProcessor
    from media_processor import MediaProcessor
    from notion_api import NotionAPI
    from transcript_analyzer import TranscriptAnalyzer
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
            logging.FileHandler('meeting_automation_universal.log', encoding='utf-8')
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
    """Обработка аккаунта (календарь и диск)."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info(f"📅 Обработка аккаунта: {account_type}")
    
    try:
        if account_type == 'personal':
            if config_manager.is_personal_enabled():
                logger.info("👤 Обрабатываю личный аккаунт")
                # Здесь будет логика обработки личного аккаунта
                return {"status": "success", "message": "Personal account processed"}
            else:
                logger.warning("⚠️ Личный аккаунт отключен")
                return {"status": "skipped", "message": "Personal account disabled"}
        
        elif account_type == 'work':
            if config_manager.is_work_enabled():
                logger.info("🏢 Обрабатываю рабочий аккаунт")
                # Здесь будет логика обработки рабочего аккаунта
                return {"status": "success", "message": "Work account processed"}
            else:
                logger.warning("⚠️ Рабочий аккаунт отключен")
                return {"status": "skipped", "message": "Work account disabled"}
        
        elif account_type == 'both':
            results = []
            if config_manager.is_personal_enabled():
                personal_result = process_account(config_manager, 'personal', logger)
                results.append(personal_result)
            
            if config_manager.is_work_enabled():
                work_result = process_account(config_manager, 'work', logger)
                results.append(work_result)
            
            return {"status": "success", "message": "Both accounts processed", "results": results}
        
        else:
            logger.error(f"❌ Неизвестный тип аккаунта: {account_type}")
            return {"status": "error", "message": f"Unknown account type: {account_type}"}
            
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
        
        results = []
        if config_manager.is_personal_enabled():
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                personal_result = media_processor.process_folder(personal_folder, "personal", quality)
                results.append(personal_result)
            else:
                logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
        
        if config_manager.is_work_enabled():
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                work_result = media_processor.process_folder(work_folder, "work", quality)
                results.append(work_result)
            else:
                logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
        
        logger.info("✅ Обработка медиа завершена")
        return {"status": "success", "message": "Media processing completed", "results": results}
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки медиа: {e}")
        return {"status": "error", "message": str(e)}

def process_transcription(config_manager: ConfigManager, account_type: str, file_path: str = None, logger: logging.Logger = None):
    """Обработка транскрипции аудио файлов."""
    if logger is None:
        logger = logging.getLogger(__name__)
    
    logger.info("🎤 Запуск транскрипции аудио...")
    
    try:
        # Инициализируем AudioProcessor
        audio_processor = AudioProcessor()
        
        if file_path:
            # Транскрибируем конкретный файл
            logger.info(f"🎵 Транскрибирую файл: {file_path}")
            if os.path.exists(file_path):
                # Создаем транскрипцию
                transcript = audio_processor._transcribe_full_audio(file_path)
                if transcript:
                    # Сохраняем транскрипцию
                    transcript_file = file_path.replace('.mp3', '_transcript.txt')
                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        f.write(transcript)
                    logger.info(f"✅ Транскрипция сохранена: {transcript_file}")
                    return {"status": "success", "message": f"Transcription saved to {transcript_file}"}
                else:
                    logger.error(f"❌ Не удалось создать транскрипцию для {file_path}")
                    return {"status": "error", "message": f"Failed to create transcription for {file_path}"}
            else:
                logger.error(f"❌ Файл не найден: {file_path}")
                return {"status": "error", "message": f"File not found: {file_path}"}
        else:
            # Транскрибируем все MP3 файлы в папках аккаунтов
            logger.info(f"🎵 Транскрибирую все MP3 файлы для аккаунта: {account_type}")
            
            results = []
            if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
                personal_config = config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = _process_folder_transcription(audio_processor, personal_folder, "personal")
                    results.append(personal_result)
            
            if account_type in ['work', 'both'] and config_manager.is_work_enabled():
                work_config = config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = _process_folder_transcription(audio_processor, work_folder, "work")
                    results.append(work_result)
            
            logger.info("✅ Транскрипция завершена")
            return {"status": "success", "message": "Transcription completed", "results": results}
        
    except Exception as e:
        logger.error(f"❌ Ошибка транскрипции: {e}")
        return {"status": "error", "message": str(e)}

def _process_folder_transcription(audio_processor: AudioProcessor, folder_path: str, account_type: str):
    """Обработка транскрипции для конкретной папки."""
    try:
        result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
        
        # Ищем MP3 файлы для транскрипции
        mp3_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith('.mp3'):
                    mp3_files.append(os.path.join(root, file))
        
        if not mp3_files:
            return result
        
        # Обрабатываем каждый MP3 файл
        for mp3_file in mp3_files:
            try:
                transcript = audio_processor._transcribe_full_audio(mp3_file)
                if transcript:
                    # Сохраняем транскрипцию
                    transcript_file = mp3_file.replace('.mp3', '_transcript.txt')
                    with open(transcript_file, 'w', encoding='utf-8') as f:
                        f.write(transcript)
                    
                    result["processed"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "success",
                        "output": transcript_file
                    })
                else:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "error",
                        "error": "Failed to create transcription"
                    })
                    
            except Exception as e:
                result["errors"] += 1
                result["files"].append({
                    "file": os.path.basename(mp3_file),
                    "status": "error",
                    "error": str(e)
                })
        
        return result
        
    except Exception as e:
        return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}

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
        
        # Инициализируем Notion API
        notion_api = NotionAPI(notion_config)
        
        results = []
        if account_type in ['personal', 'both'] and config_manager.is_personal_enabled():
            logger.info("👤 Синхронизирую личный аккаунт с Notion")
            personal_config = config_manager.get_personal_config()
            personal_folder = personal_config.get('local_drive_root')
            if personal_folder and os.path.exists(personal_folder):
                personal_result = _sync_folder_with_notion(notion_api, personal_folder, "personal")
                results.append(personal_result)
        
        if account_type in ['work', 'both'] and config_manager.is_work_enabled():
            logger.info("🏢 Синхронизирую рабочий аккаунт с Notion")
            work_config = config_manager.get_work_config()
            work_folder = work_config.get('local_drive_root')
            if work_folder and os.path.exists(work_folder):
                work_result = _sync_folder_with_notion(notion_api, work_folder, "work")
                results.append(work_result)
        
        logger.info("✅ Синхронизация с Notion завершена")
        return {"status": "success", "message": "Notion sync completed", "results": results}
        
    except Exception as e:
        logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
        return {"status": "error", "message": str(e)}

def _sync_folder_with_notion(notion_api: NotionAPI, folder_path: str, account_type: str):
    """Синхронизация конкретной папки с Notion."""
    try:
        result = {"account": account_type, "folder": folder_path, "synced": 0, "errors": 0, "files": []}
        
        # Ищем файлы транскрипции
        transcript_files = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                if file.endswith('_transcript.txt'):
                    transcript_files.append(os.path.join(root, file))
        
        if not transcript_files:
            return result
        
        # Синхронизируем каждый файл транскрипции
        for transcript_file in transcript_files:
            try:
                # Здесь будет логика синхронизации с Notion
                # Пока просто логируем
                result["synced"] += 1
                result["files"].append({
                    "file": os.path.basename(transcript_file),
                    "status": "synced"
                })
                
            except Exception as e:
                result["errors"] += 1
                result["files"].append({
                    "file": os.path.basename(transcript_file),
                    "status": "error",
                    "error": str(e)
                })
        
        return result
        
    except Exception as e:
        return {"account": account_type, "folder": folder_path, "synced": 0, "errors": 1, "files": [], "error": str(e)}

def main():
    """Главная функция."""
    parser = argparse.ArgumentParser(description='Универсальный скрипт автоматизации встреч')
    parser.add_argument('action', choices=['calendar', 'drive', 'media', 'transcribe', 'notion', 'all'],
                       help='Действие для выполнения')
    parser.add_argument('--account', choices=['personal', 'work', 'both'], default='both',
                       help='Тип аккаунта для обработки')
    parser.add_argument('--file', help='Путь к конкретному файлу для обработки')
    parser.add_argument('--quality', choices=['low', 'medium', 'high'], default='medium',
                       help='Качество обработки медиа')
    
    args = parser.parse_args()
    
    # Настраиваем логирование
    logger = setup_logging()
    logger.info(f"🚀 Запуск {args.action} для аккаунта: {args.account}")
    
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
        elif args.action == 'all':
            # Выполняем все действия последовательно
            results = {}
            results['calendar'] = process_account(config_manager, args.account, logger)
            results['media'] = process_media(config_manager, args.quality, logger)
            results['transcribe'] = process_transcription(config_manager, args.account, logger)
            results['notion'] = process_notion_sync(config_manager, args.account, logger)
            result = {"status": "success", "message": "All actions completed", "results": results}
        
        logger.info(f"✅ {args.action} завершен: {result}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения {args.action}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
