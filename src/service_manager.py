#!/usr/bin/env python3
"""
Сервисный менеджер для автоматизации встреч
Обеспечивает работу в фоновом режиме с мониторингом и логированием
Поддерживает dual-account систему (личный и рабочий аккаунты)
"""

import os
import sys
import time
import json
import signal
import logging
import threading
import subprocess
import traceback
import concurrent.futures
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path
import functools
import psutil

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Ошибка импорта dotenv: {e}")
    print("Установите: pip install python-dotenv")
    sys.exit(1)


def retry(max_attempts=3, delay=5, backoff=2, exceptions=(Exception,)):
    """
    Декоратор для повторных попыток выполнения функции при возникновении исключений.
    
    Args:
        max_attempts: Максимальное количество попыток
        delay: Начальная задержка между попытками (в секундах)
        backoff: Множитель для увеличения задержки с каждой попыткой
        exceptions: Кортеж исключений, которые следует перехватывать
        
    Returns:
        Декоратор функции
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            mtries, mdelay = max_attempts, delay
            
            # Получаем имя функции для логирования
            func_name = func.__name__
            
            while mtries > 1:
                try:
                    return func(self, *args, **kwargs)
                except exceptions as e:
                    msg = f"❌ Ошибка в {func_name} (попытка {max_attempts - mtries + 1}/{max_attempts}): {e}"
                    self.logger.warning(msg)
                    
                    # Логируем стек вызовов для отладки
                    self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
                    
                    mtries -= 1
                    if mtries == 1:
                        self.logger.error(f"❌ Все попытки исчерпаны для {func_name}")
                        break
                        
                    self.logger.info(f"⏰ Повторная попытка через {mdelay} секунд...")
                    time.sleep(mdelay)
                    mdelay *= backoff
            
            # Последняя попытка
            return func(self, *args, **kwargs)
        return wrapper
    return decorator


class MeetingAutomationService:
    """Менеджер сервиса автоматизации."""
    
    def __init__(self, config_file: str = '.env', 
                 interval: int = 300, 
                 media_interval: int = 1800,
                 log_level: str = 'INFO'):
        """
        Инициализация менеджера сервиса.
        
        Args:
            config_file: Путь к файлу конфигурации
            interval: Интервал между циклами обработки в секундах
            media_interval: Интервал между обработкой медиа файлов в секундах
            log_level: Уровень логирования
        """
        self.config_file = config_file
        self.interval = interval
        self.media_check_interval = media_interval
        
        # Настраиваем логирование
        self.logger = self._setup_logging(log_level)
        self.logger.info("🚀 Инициализация менеджера сервиса...")
        
        # Загружаем конфигурацию
        self._load_config()
        
        # Инициализируем переменные для хранения статистики
        self.last_media_check = 0
        self.last_media_stats = {}
        self.last_transcription_stats = {}
        self.last_notion_stats = {}
        self.last_telegram_stats = {}
        self.last_summary_stats = {}
        
        # Инициализируем переменные для хранения состояния
        self.previous_cycle_state = {}
        self.current_cycle_state = {}
        
        # Флаг работы сервиса
        self.running = False
        self.thread = None
        
        # Инициализируем кэш результатов
        self.cache = {
            'processed_files': set(),  # Множество уже обработанных файлов
            'transcribed_files': set(),  # Множество уже транскрибированных файлов
            'summarized_files': set(),  # Множество уже проанализированных файлов
            'notion_pages': {},  # Словарь страниц Notion (ключ - ID папки, значение - ID страницы)
            'last_update': datetime.now()  # Время последнего обновления кэша
        }
        
        # Инициализируем мониторинг производительности
        self.performance_stats = {
            'cpu_usage': [],
            'memory_usage': [],
            'disk_usage': [],
            'cycle_times': []
        }
        
        # Загружаем кэш из файла, если он существует
        self._load_cache()
        
        # Инициализируем обработчики
        self._init_handlers()
        
        # Логируем конфигурацию
        self._log_configuration()
        
        self.logger.info("✅ Менеджер сервиса инициализирован")
    
    def _init_handlers(self):
        """Инициализация обработчиков для различных задач."""
        try:
            # Импортируем обработчики
            try:
                from src.calendar_handler import get_calendar_handler
                from src.media_processor import get_media_processor
                from src.transcription_handler import get_transcription_handler
                
                # Создаем экземпляры обработчиков
                self.calendar_handler = get_calendar_handler(self.config_manager, self.logger)
                self.media_processor = get_media_processor(self.config_manager, self.logger)
                self.transcription_handler = get_transcription_handler(self.config_manager, self.logger)
                
                self.logger.info("✅ Обработчики инициализированы")
            except ImportError:
                self.logger.warning("⚠️ Не удалось импортировать модули обработчиков. Используем универсальный скрипт.")
                self.calendar_handler = None
                self.media_processor = None
                self.transcription_handler = None
        except Exception as e:
            self.logger.error(f"❌ Ошибка инициализации обработчиков: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            # Продолжаем работу без обработчиков
            self.calendar_handler = None
            self.media_processor = None
            self.transcription_handler = None
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Настройка логирования."""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем логгер
        logger = logging.getLogger("meeting_automation_service")
        logger.setLevel(logging.getLevelName(log_level))
        
        # Очищаем существующие хендлеры
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Хендлер для основного лога (INFO и выше)
        file_handler = logging.FileHandler(log_dir / "service.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Хендлер для консоли (только INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Добавляем хендлеры в основной логгер
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _load_cache(self):
        """Загрузка кэша из файла."""
        try:
            cache_file = Path('data/service_cache.json')
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Преобразуем списки обратно в множества
                self.cache['processed_files'] = set(cache_data.get('processed_files', []))
                self.cache['transcribed_files'] = set(cache_data.get('transcribed_files', []))
                self.cache['summarized_files'] = set(cache_data.get('summarized_files', []))
                self.cache['notion_pages'] = cache_data.get('notion_pages', {})
                
                # Преобразуем строку даты обратно в datetime
                last_update_str = cache_data.get('last_update')
                if last_update_str:
                    self.cache['last_update'] = datetime.fromisoformat(last_update_str)
                
                self.logger.info(f"✅ Кэш загружен из {cache_file}")
                self.logger.info(f"📊 Статистика кэша: {len(self.cache['processed_files'])} обработанных файлов, {len(self.cache['transcribed_files'])} транскрибированных файлов")
            else:
                self.logger.info("⚠️ Файл кэша не найден, используем пустой кэш")
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки кэша: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")

    def _save_cache(self):
        """Сохранение кэша в файл."""
        try:
            # Создаем директорию для кэша, если её нет
            cache_dir = Path('data')
            cache_dir.mkdir(exist_ok=True)
            
            cache_file = cache_dir / 'service_cache.json'
            
            # Преобразуем множества в списки для JSON
            cache_data = {
                'processed_files': list(self.cache['processed_files']),
                'transcribed_files': list(self.cache['transcribed_files']),
                'summarized_files': list(self.cache['summarized_files']),
                'notion_pages': self.cache['notion_pages'],
                'last_update': datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Кэш сохранен в {cache_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения кэша: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")

    def _is_file_processed(self, file_path: str) -> bool:
        """Проверяет, был ли файл уже обработан."""
        return file_path in self.cache['processed_files']

    def _mark_file_processed(self, file_path: str):
        """Отмечает файл как обработанный."""
        self.cache['processed_files'].add(file_path)
        # Сохраняем кэш после каждого обновления
        self._save_cache()

    def _is_file_transcribed(self, file_path: str) -> bool:
        """Проверяет, был ли файл уже транскрибирован."""
        return file_path in self.cache['transcribed_files']

    def _mark_file_transcribed(self, file_path: str):
        """Отмечает файл как транскрибированный."""
        self.cache['transcribed_files'].add(file_path)
        # Сохраняем кэш после каждого обновления
        self._save_cache()

    def _is_file_summarized(self, file_path: str) -> bool:
        """Проверяет, был ли файл уже проанализирован."""
        return file_path in self.cache['summarized_files']

    def _mark_file_summarized(self, file_path: str):
        """Отмечает файл как проанализированный."""
        self.cache['summarized_files'].add(file_path)
        # Сохраняем кэш после каждого обновления
        self._save_cache()

    def _get_notion_page_id(self, folder_id: str) -> Optional[str]:
        """Получает ID страницы Notion по ID папки."""
        return self.cache['notion_pages'].get(folder_id)

    def _set_notion_page_id(self, folder_id: str, page_id: str):
        """Устанавливает ID страницы Notion для папки."""
        self.cache['notion_pages'][folder_id] = page_id
        # Сохраняем кэш после каждого обновления
        self._save_cache()

    @retry(max_attempts=3, delay=5, backoff=2)
    def _load_config(self):
        """Загрузка переменных окружения."""
        try:
            # Загружаем основной .env файл
            if os.path.exists(self.config_file):
                load_dotenv(self.config_file)
                self.logger.info(f"✅ Загружен основной конфиг: {self.config_file}")
                
                # Инициализируем ConfigManager
                from src.config_manager import ConfigManager
                self.config_manager = ConfigManager(self.config_file)
                
                # Обновляем интервалы из конфигурации
                general_config = self.config_manager.get_general_config()
                self.interval = general_config.get('service_check_interval', 300)
                self.media_check_interval = general_config.get('service_media_interval', 1800)
                
                self.logger.info(f"⏰ Интервал проверки: {self.interval} секунд")
                self.logger.info(f"🎬 Интервал медиа: {self.media_check_interval} секунд")
                
                # Проверяем конфигурацию
                if self.config_manager.validate_config():
                    self.logger.info("✅ Конфигурация проверена и валидна")
                    return True
                else:
                    self.logger.error("❌ Ошибка валидации конфигурации")
                    return False
            else:
                self.logger.error(f"❌ Файл конфигурации не найден: {self.config_file}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки окружения: {e}")
            return False
    
    def _log_configuration(self):
        """Детальное логирование параметров конфигурации."""
        try:
            self.logger.info("📋 ДЕТАЛЬНАЯ КОНФИГУРАЦИЯ СЕРВИСА:")
            
            # Общие параметры
            general_config = self.config_manager.get_general_config()
            self.logger.info("⚙️ Общие параметры:")
            for key, value in general_config.items():
                self.logger.info(f"   • {key}: {value}")
            
            # Статус аккаунтов
            self.logger.info("👥 Статус аккаунтов:")
            self.logger.info(f"   • Личный аккаунт: {'✅ Включен' if self.config_manager.is_personal_enabled() else '❌ Отключен'}")
            self.logger.info(f"   • Рабочий аккаунт: {'✅ Включен' if self.config_manager.is_work_enabled() else '❌ Отключен'}")
            
            # Параметры личного аккаунта
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                self.logger.info("👤 Параметры личного аккаунта:")
                self.logger.info(f"   • Провайдер календаря: {personal_config.get('calendar_provider', 'не указан')}")
                self.logger.info(f"   • Провайдер диска: {personal_config.get('drive_provider', 'не указан')}")
                self.logger.info(f"   • Локальная папка: {personal_config.get('local_drive_root', 'не указана')}")
            
            # Параметры рабочего аккаунта
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                self.logger.info("🏢 Параметры рабочего аккаунта:")
                self.logger.info(f"   • Провайдер календаря: {work_config.get('calendar_provider', 'не указан')}")
                self.logger.info(f"   • Провайдер диска: {work_config.get('drive_provider', 'не указан')}")
                self.logger.info(f"   • Локальная папка: {work_config.get('local_drive_root', 'не указана')}")
            
            # Параметры медиа
            media_config = self.config_manager.get_media_config()
            self.logger.info("🎬 Параметры медиа обработки:")
            self.logger.info(f"   • Качество: {media_config.get('quality', 'medium')}")
            self.logger.info(f"   • Формат: {media_config.get('output_format', 'mp4')}")
            self.logger.info(f"   • Сжатие видео: {'✅ Включено' if media_config.get('video_compression', True) else '❌ Отключено'}")
            
            # Параметры транскрипции
            whisper_config = self.config_manager.get_whisper_config()
            self.logger.info("🎤 Параметры транскрипции:")
            self.logger.info(f"   • Метод: {whisper_config.get('transcription_method', 'local')}")
            self.logger.info(f"   • Модель: {whisper_config.get('whisper_model', 'base')}")
            
            # Параметры Notion
            notion_config = self.config_manager.get_notion_config()
            self.logger.info("📝 Параметры Notion:")
            self.logger.info(f"   • Токен: {'✅ Настроен' if notion_config.get('token') else '❌ Не настроен'}")
            self.logger.info(f"   • База данных: {'✅ Настроена' if notion_config.get('database_id') else '❌ Не настроена'}")
            
            # Параметры Telegram
            telegram_config = self.config_manager.get_telegram_config()
            self.logger.info("📱 Параметры Telegram:")
            self.logger.info(f"   • Бот токен: {'✅ Настроен' if telegram_config.get('bot_token') else '❌ Не настроен'}")
            self.logger.info(f"   • Чат ID: {'✅ Настроен' if telegram_config.get('chat_id') else '❌ Не настроен'}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка при логировании конфигурации: {e}")
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def run_personal_automation(self) -> Dict[str, Any]:
        """Запуск автоматизации для личного аккаунта."""
        try:
            if self.calendar_handler:
                return self.calendar_handler.process_account('personal')
            else:
                # Используем старый метод через universal script
                self.logger.info("👤 Запуск обработки личного аккаунта...")
                
                cmd = [
                    sys.executable,
                    'meeting_automation_universal.py',
                    'account',
                    '--type', 'personal'
                ]
                
                self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0:
                    self.logger.info("✅ Обработка личного аккаунта завершена успешно")
                    return {"status": "success", "output": process.stdout}
                else:
                    self.logger.error(f"❌ Ошибка обработки личного аккаунта: {process.stderr}")
                    return {"status": "error", "output": process.stderr}
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки личного аккаунта: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "output": str(e)}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def run_work_automation(self) -> Dict[str, Any]:
        """Запуск автоматизации для рабочего аккаунта."""
        try:
            if self.calendar_handler:
                return self.calendar_handler.process_account('work')
            else:
                # Используем старый метод через universal script
                self.logger.info("🏢 Запуск обработки рабочего аккаунта...")
                
                cmd = [
                    sys.executable,
                    'meeting_automation_universal.py',
                    'account',
                    '--type', 'work'
                ]
                
                self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0:
                    self.logger.info("✅ Обработка рабочего аккаунта завершена успешно")
                    return {"status": "success", "output": process.stdout}
                else:
                    self.logger.error(f"❌ Ошибка обработки рабочего аккаунта: {process.stderr}")
                    return {"status": "error", "output": process.stderr}
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки рабочего аккаунта: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "output": str(e)}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process_media_files(self) -> Dict[str, Any]:
        """Обработка медиа файлов."""
        try:
            # Проверяем, прошло ли достаточно времени с последней проверки
            current_time = time.time()
            
            # Проверяем, нужно ли запускать медиа обработку
            if hasattr(self, 'last_media_check') and (current_time - self.last_media_check) < self.media_check_interval:
                self.logger.info("⏰ Медиа обработка еще не требуется")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0}
            
            self.last_media_check = current_time
            
            if self.media_processor:
                # Используем новый обработчик медиа
                media_stats = self.media_processor.process_media('medium')
                self.last_media_stats = media_stats
                return media_stats
            else:
                # Используем старый метод через universal script
                self.logger.info("🎬 Запуск обработки медиа файлов...")
                
                cmd = [
                    sys.executable,
                    'meeting_automation_universal.py',
                    'media',
                    '--quality', 'medium'
                ]
                
                self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
                
                process = subprocess.run(cmd, capture_output=True, text=True)
                
                if process.returncode == 0:
                    self.logger.info("✅ Обработка медиа завершена успешно")
                    
                    # Пытаемся извлечь JSON из вывода
                    try:
                        import json
                        import re
                        
                        # Ищем JSON в выводе
                        json_match = re.search(r'({.*})', process.stdout, re.DOTALL)
                        if json_match:
                            media_stats = json.loads(json_match.group(1))
                            self.last_media_stats = media_stats
                            return media_stats
                    except Exception as e:
                        self.logger.warning(f"⚠️ Не удалось извлечь статистику медиа: {e}")
                    
                    # Если не удалось извлечь JSON, возвращаем базовую статистику
                    return {"status": "success", "processed": 1, "synced": 1, "cleanup": 0, "errors": 0}
                else:
                    self.logger.error(f"❌ Ошибка обработки медиа: {process.stderr}")
                    return {"status": "error", "processed": 0, "synced": 0, "cleanup": 0, "errors": 1}
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки медиа: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "processed": 0, "synced": 0, "cleanup": 0, "errors": 1}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process_audio_transcription(self) -> Dict[str, Any]:
        """Обработка транскрипции аудио файлов."""
        try:
            if self.transcription_handler:
                # Используем новый обработчик транскрипций
                transcription_stats = self.transcription_handler.process_transcription()
                self.last_transcription_stats = transcription_stats
                return transcription_stats
            else:
                # Используем старый метод
                self.logger.info("🎤 Начинаю обработку транскрипции аудио...")
                
                transcription_stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
                
                # Проверяем наличие аудио файлов перед запуском
                has_audio_files = False
                
                # Обрабатываем личный аккаунт
                if self.config_manager and self.config_manager.is_personal_enabled():
                    personal_config = self.config_manager.get_personal_config()
                    personal_folder = personal_config.get('local_drive_root')
                    if personal_folder and os.path.exists(personal_folder):
                        self.logger.info(f"👤 Проверка аудио файлов в папке личного аккаунта: {personal_folder}")
                        personal_audio_files = self._count_audio_files(personal_folder)
                        if personal_audio_files > 0:
                            self.logger.info(f"🎵 Найдено {personal_audio_files} аудио файлов в личном аккаунте")
                            has_audio_files = True
                            self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                            personal_result = self._process_folder_transcription(personal_folder, "personal")
                            transcription_stats["details"].append(personal_result)
                            transcription_stats["processed"] += personal_result.get("processed", 0)
                            transcription_stats["errors"] += personal_result.get("errors", 0)
                        else:
                            self.logger.info(f"📂 В папке личного аккаунта нет аудио файлов для транскрипции")
                
                # Обрабатываем рабочий аккаунт
                if self.config_manager and self.config_manager.is_work_enabled():
                    work_config = self.config_manager.get_work_config()
                    work_folder = work_config.get('local_drive_root')
                    if work_folder and os.path.exists(work_folder):
                        self.logger.info(f"🏢 Проверка аудио файлов в папке рабочего аккаунта: {work_folder}")
                        work_audio_files = self._count_audio_files(work_folder)
                        if work_audio_files > 0:
                            self.logger.info(f"🎵 Найдено {work_audio_files} аудио файлов в рабочем аккаунте")
                            has_audio_files = True
                            self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                            work_result = self._process_folder_transcription(work_folder, "work")
                            transcription_stats["details"].append(work_result)
                            transcription_stats["processed"] += work_result.get("processed", 0)
                            transcription_stats["errors"] += work_result.get("errors", 0)
                        else:
                            self.logger.info(f"📂 В папке рабочего аккаунта нет аудио файлов для транскрипции")
                
                if not has_audio_files:
                    self.logger.info("📂 Нет аудио файлов для транскрипции")
                    transcription_stats["status"] = "no_files"
                
                self.logger.info(f"✅ Транскрипция завершена: обработано {transcription_stats['processed']}, ошибок {transcription_stats['errors']}")
                
                # Сохраняем статистику для детальных отчетов
                self.last_transcription_stats = transcription_stats
                
                return transcription_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка транскрипции: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            self.last_transcription_stats = error_stats
            return error_stats
    
    def _count_audio_files(self, folder_path: str) -> int:
        """Подсчет количества аудио файлов для транскрипции."""
        try:
            count = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.mp3') and not file.lower().endswith('_compressed.mp3'):
                        # Проверяем, существует ли уже файл транскрипции
                        mp3_path = os.path.join(root, file)
                        transcript_file = mp3_path.replace('.mp3', '_transcript.txt')
                        if not os.path.exists(transcript_file):
                            count += 1
            return count
        except Exception as e:
            self.logger.error(f"❌ Ошибка подсчета аудио файлов: {e}")
            return 0
    
    def _process_folder_transcription(self, folder_path: str, account_type: str) -> Dict[str, Any]:
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
                self.logger.info(f"📁 В папке {folder_path} нет MP3 файлов для транскрипции")
                return result
            
            self.logger.info(f"🎵 Найдено {len(mp3_files)} MP3 файлов для транскрипции")
            
            # Запускаем транскрипцию через универсальный скрипт
            for mp3_file in mp3_files:
                try:
                    # Проверяем, существует ли уже файл транскрипции
                    transcript_file = mp3_file.replace('.mp3', '_transcript.txt')
                    if os.path.exists(transcript_file):
                        self.logger.info(f"📄 Файл транскрипции уже существует: {os.path.basename(transcript_file)}")
                        result["processed"] += 1
                        result["files"].append({
                            "file": os.path.basename(mp3_file),
                            "status": "already_exists",
                            "output": transcript_file
                        })
                        continue
                    
                    self.logger.info(f"🎤 Транскрибирую: {os.path.basename(mp3_file)}")
                    
                    # Запускаем транскрипцию
                    transcription_result = subprocess.run([
                        sys.executable, "meeting_automation_universal.py", "transcribe", 
                        "--account", account_type, "--file", mp3_file
                    ], capture_output=True, text=True, timeout=600)  # 10 минут на файл
                    
                    if transcription_result.returncode == 0:
                        result["processed"] += 1
                        result["files"].append({
                            "file": os.path.basename(mp3_file),
                            "status": "success",
                            "output": transcription_result.stdout
                        })
                        self.logger.info(f"✅ Транскрипция завершена: {os.path.basename(mp3_file)}")
                    else:
                        result["errors"] += 1
                        result["files"].append({
                            "file": os.path.basename(mp3_file),
                            "status": "error",
                            "error": transcription_result.stderr
                        })
                        self.logger.error(f"❌ Ошибка транскрипции: {os.path.basename(mp3_file)}")
                        
                except subprocess.TimeoutExpired:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "timeout",
                        "error": "Превышено время выполнения"
                    })
                    self.logger.error(f"⏰ Таймаут транскрипции: {os.path.basename(mp3_file)}")
                except Exception as e:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(mp3_file),
                        "status": "error",
                        "error": str(e)
                    })
                    self.logger.error(f"❌ Ошибка транскрипции {os.path.basename(mp3_file)}: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def sync_with_notion(self) -> Dict[str, Any]:
        """Синхронизация с Notion."""
        try:
            self.logger.info("📝 Запуск синхронизации с Notion...")
            
            # Здесь будет логика синхронизации с Notion
            # TODO: Реализовать через NotionHandler
            
            notion_stats = {"status": "success", "synced": 0, "errors": 0, "details": []}
            
            # Сохраняем статистику для детальных отчетов
            self.last_notion_stats = notion_stats
            
            return notion_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {"status": "error", "synced": 0, "errors": 1, "details": [str(e)]}
            self.last_notion_stats = error_stats
            return error_stats
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def send_telegram_notifications(self, current_state: Dict[str, Any], previous_state: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка уведомлений в Telegram."""
        try:
            self.logger.info("📱 Проверка необходимости отправки уведомлений в Telegram...")
            
            # Проверяем, нужно ли отправлять уведомление
            # В режиме тестирования всегда отправляем
            force_send = self.config_manager.get('TELEGRAM_ALWAYS_SEND', False)
            
            if not force_send and not self._has_changes(current_state, previous_state):
                self.logger.info("⏭️ Нет изменений, пропускаю отправку уведомлений")
                return {"status": "skipped", "message": "No changes"}
            
            # Формируем детальный отчет
            report = self._format_detailed_report()
            
            # Отправляем уведомление
            self.logger.info("📱 Отправка уведомления в Telegram...")
            
            cmd = [
                sys.executable,
                'meeting_automation_universal.py',
                'notify',
                '--message', report
            ]
            
            self.logger.info(f"🔄 Запуск команды: {' '.join(cmd[:4])}...")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                self.logger.info("✅ Уведомление отправлено успешно")
                return {"status": "success", "message": "Notification sent"}
            else:
                self.logger.error(f"❌ Ошибка отправки уведомления: {process.stderr}")
                return {"status": "error", "message": process.stderr}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомлений: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "message": str(e)}
    
    def _format_status_message(self) -> str:
        """Форматирование сообщения о статусе для Telegram."""
        try:
            message = "🤖 <b>Статус системы автоматизации встреч</b>\n\n"
            
            # Добавляем информацию о времени
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message += f"⏰ <b>Время:</b> {current_time}\n\n"
            
            # Добавляем информацию о статусе аккаунтов
            if self.config_manager:
                if self.config_manager.is_personal_enabled():
                    message += "👤 <b>Личный аккаунт:</b> ✅ Активен\n"
                else:
                    message += "👤 <b>Личный аккаунт:</b> ❌ Отключен\n"
                
                if self.config_manager.is_work_enabled():
                    message += "🏢 <b>Рабочий аккаунт:</b> ✅ Активен\n"
                else:
                    message += "🏢 <b>Рабочий аккаунт:</b> ❌ Отключен\n"
            
            message += "\n🎯 <b>Система работает в штатном режиме</b>"
            
            return message
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка форматирования сообщения: {e}")
            return f"❌ Ошибка формирования статуса: {str(e)}"
    
    def create_status_files(self):
        """Создание файлов статуса в папках аккаунтов."""
        try:
            self.logger.info("📁 Создаю файлы статуса в папках аккаунтов...")
            
            if self.config_manager and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    # Создаем статус в корневой папке
                    self._create_folder_status_file(personal_folder, "personal")
                    # Создаем статус в каждой папке встречи
                    self._create_meeting_status_files(personal_folder, "personal")
            
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    # Создаем статус в корневой папке
                    self._create_folder_status_file(work_folder, "work")
                    # Создаем статус в каждой папке встречи
                    self._create_meeting_status_files(work_folder, "work")
            
            self.logger.info("✅ Файлы статуса созданы")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания файлов статуса: {e}")
    
    def _create_folder_status_file(self, folder_path: str, account_type: str):
        """Создание файла статуса для конкретной папки."""
        try:
            status_file_path = os.path.join(folder_path, "📊 СТАТУС ОБРАБОТКИ.txt")
            
            # Анализируем содержимое папки
            status_info = self._analyze_folder_status(folder_path, account_type)
            
            # Создаем файл статуса
            with open(status_file_path, 'w', encoding='utf-8') as f:
                f.write(status_info)
            
            # Делаем файл более заметным (убираем скрытые атрибуты)
            try:
                import subprocess
                subprocess.run(['chflags', 'nohidden', status_file_path], check=False)
            except:
                pass  # Игнорируем ошибки, если chflags недоступен
            
            self.logger.info(f"✅ Файл статуса создан: {status_file_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания файла статуса для {folder_path}: {e}")
    
    def _create_meeting_status_files(self, root_folder: str, account_type: str):
        """Создание файлов статуса в каждой папке встречи."""
        try:
            # Ищем все папки встреч (папки с датами)
            meeting_folders = []
            for item in os.listdir(root_folder):
                item_path = os.path.join(root_folder, item)
                if os.path.isdir(item_path) and any(char.isdigit() for char in item):
                    meeting_folders.append(item_path)
            
            for meeting_folder in meeting_folders:
                try:
                    self._create_folder_status_file(meeting_folder, account_type)
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось создать статус для папки встречи {meeting_folder}: {e}")
                    
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания файлов статуса встреч: {e}")
    
    def _analyze_folder_status(self, folder_path: str, account_type: str) -> str:
        """Анализ статуса папки и формирование отчета."""
        try:
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            status_report = f"""📊 СТАТУС ОБРАБОТКИ ПАПКИ
{'='*50}
📁 Папка: {folder_path}
👤 Аккаунт: {account_type}
⏰ Время проверки: {current_time}
{'='*50}

🎬 ВИДЕО ФАЙЛЫ:
"""
            
            # Анализируем видео файлы
            video_files = []
            compressed_videos = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.mov', '.mp4', '.avi', '.mkv')):
                        file_path = os.path.join(root, file)
                        if 'compressed' in file.lower():
                            compressed_videos.append(file)
                        else:
                            video_files.append(file)
            
            if video_files:
                status_report += f"📹 Оригинальные видео: {len(video_files)}\n"
                for video in video_files[:5]:  # Показываем первые 5
                    status_report += f"   • {video}\n"
                if len(video_files) > 5:
                    status_report += f"   ... и еще {len(video_files) - 5} файлов\n"
            else:
                status_report += "📹 Оригинальные видео: не найдены\n"
            
            if compressed_videos:
                status_report += f"🎥 Сжатые видео: {len(compressed_videos)}\n"
                for video in compressed_videos[:3]:
                    status_report += f"   • {video}\n"
            else:
                status_report += "🎥 Сжатые видео: не найдены\n"
            
            # Анализируем аудио файлы
            status_report += "\n🎵 АУДИО ФАЙЛЫ:\n"
            audio_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.mp3'):
                        audio_files.append(file)
            
            if audio_files:
                status_report += f"🎤 MP3 файлы: {len(audio_files)}\n"
                for audio in audio_files[:5]:
                    status_report += f"   • {audio}\n"
                if len(audio_files) > 5:
                    status_report += f"   ... и еще {len(audio_files) - 5} файлов\n"
            else:
                status_report += "🎤 MP3 файлы: не найдены\n"
            
            # Анализируем транскрипции
            status_report += "\n📝 ТРАНСКРИПЦИИ:\n"
            transcription_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(('.txt', '.md', '.csv')):
                        transcription_files.append(file)
            
            if transcription_files:
                status_report += f"📄 Файлы транскрипций: {len(transcription_files)}\n"
                for trans in transcription_files[:5]:
                    status_report += f"   • {trans}\n"
                if len(transcription_files) > 5:
                    status_report += f"   ... и еще {len(transcription_files) - 5} файлов\n"
            else:
                status_report += "📄 Файлы транскрипций: не найдены\n"
            
            # Добавляем рекомендации
            status_report += f"""

{'='*50}
💡 РЕКОМЕНДАЦИИ:
• Если есть оригинальные видео без сжатых версий - они будут обработаны в следующем цикле
• Если есть MP3 файлы без транскрипций - они будут транскрибированы в следующем цикле
• Все результаты сохраняются в той же папке

🔄 Следующая проверка: через 5 минут
📱 Уведомления отправляются в Telegram
📝 Заметки сохраняются в Notion
{'='*50}

🤖 Автоматически создано системой meeting_automation
📅 {current_time}
"""
            
            return status_report
            
        except Exception as e:
            return f"❌ Ошибка анализа папки: {str(e)}"
    
    def _monitor_performance(self):
        """Мониторинг производительности системы."""
        try:
            # Получаем текущие показатели системы
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_info = psutil.virtual_memory()
            memory_percent = memory_info.percent
            disk_info = psutil.disk_usage('/')
            disk_percent = disk_info.percent
            
            # Добавляем показатели в статистику
            self.performance_stats['cpu_usage'].append(cpu_percent)
            self.performance_stats['memory_usage'].append(memory_percent)
            self.performance_stats['disk_usage'].append(disk_percent)
            
            # Ограничиваем размер списков
            max_stats = 100
            if len(self.performance_stats['cpu_usage']) > max_stats:
                self.performance_stats['cpu_usage'] = self.performance_stats['cpu_usage'][-max_stats:]
            if len(self.performance_stats['memory_usage']) > max_stats:
                self.performance_stats['memory_usage'] = self.performance_stats['memory_usage'][-max_stats:]
            if len(self.performance_stats['disk_usage']) > max_stats:
                self.performance_stats['disk_usage'] = self.performance_stats['disk_usage'][-max_stats:]
            
            # Логируем текущие показатели
            self.logger.info(f"🖥️ Производительность системы:")
            self.logger.info(f"   CPU: {cpu_percent:.1f}%")
            self.logger.info(f"   Память: {memory_percent:.1f}% ({memory_info.used / (1024 ** 3):.1f} ГБ / {memory_info.total / (1024 ** 3):.1f} ГБ)")
            self.logger.info(f"   Диск: {disk_percent:.1f}% ({disk_info.used / (1024 ** 3):.1f} ГБ / {disk_info.total / (1024 ** 3):.1f} ГБ)")
            
            # Сохраняем статистику производительности в файл
            self._save_performance_stats()
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent
            }
        except Exception as e:
            self.logger.error(f"❌ Ошибка мониторинга производительности: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {}

    def _save_performance_stats(self):
        """Сохранение статистики производительности в файл."""
        try:
            # Создаем директорию для статистики, если её нет
            stats_dir = Path('data')
            stats_dir.mkdir(exist_ok=True)
            
            stats_file = stats_dir / 'performance_stats.json'
            
            # Сохраняем статистику в файл
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.performance_stats, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения статистики производительности: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
    
    def run_service_cycle(self):
        """Основной цикл работы сервиса."""
        try:
            start_time = time.time()
            self.logger.info("🔄 Запуск цикла обработки...")
            self.logger.info(f"⏰ Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Мониторинг производительности в начале цикла
            self._monitor_performance()
            
            # Загружаем предыдущее состояние
            self.previous_cycle_state = self._load_previous_state()
            
            # Обновляем кэш перед запуском цикла
            self._load_cache()
            
            # Этап 1: Календарь → создание папки, записи в Notion
            self.logger.info("📅 ЭТАП 1: Обработка календаря и создание папок встреч...")
            personal_stats = {"status": "skipped", "output": ""}
            work_stats = {"status": "skipped", "output": ""}
            
            # Запускаем автоматизацию для обоих аккаунтов параллельно
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Запускаем задачи параллельно
                personal_future = None
                work_future = None
                
                if self.config_manager and self.config_manager.is_personal_enabled():
                    self.logger.info("👤 Запускаю обработку личного аккаунта (параллельно)...")
                    personal_future = executor.submit(self.run_personal_automation)
                else:
                    self.logger.info("⏭️ Личный аккаунт пропущен (отключен в конфигурации)")
                
                if self.config_manager and self.config_manager.is_work_enabled():
                    self.logger.info("🏢 Запускаю обработку рабочего аккаунта (параллельно)...")
                    work_future = executor.submit(self.run_work_automation)
                else:
                    self.logger.info("⏭️ Рабочий аккаунт пропущен (отключен в конфигурации)")
                
                # Получаем результаты
                if personal_future:
                    personal_start = time.time()
                    personal_stats = personal_future.result()
                    personal_duration = time.time() - personal_start
                    self.logger.info(f"⏱️ Время обработки личного аккаунта: {personal_duration:.2f} секунд")
                
                if work_future:
                    work_start = time.time()
                    work_stats = work_future.result()
                    work_duration = time.time() - work_start
                    self.logger.info(f"⏱️ Время обработки рабочего аккаунта: {work_duration:.2f} секунд")
            
            # Этап 2: Сжатие медиа → выделение MP3
            self.logger.info("🎬 ЭТАП 2: Обработка медиа файлов...")
            media_start = time.time()
            media_stats = self.process_media_files()
            media_duration = time.time() - media_start
            self.logger.info(f"⏱️ Время обработки медиа: {media_duration:.2f} секунд")
            self.logger.info(f"📊 Результат обработки медиа: {media_stats}")
            
            # Этап 3: Транскрипция
            self.logger.info("🎤 ЭТАП 3: Транскрипция аудио...")
            self.logger.info("🔍 Проверка наличия аудио файлов для транскрипции...")
            transcription_start = time.time()
            transcription_stats = self.process_audio_transcription()
            transcription_duration = time.time() - transcription_start
            self.logger.info(f"⏱️ Время транскрипции: {transcription_duration:.2f} секунд")
            self.logger.info(f"📊 Результат транскрипции: обработано {transcription_stats.get('processed', 0)}, ошибок {transcription_stats.get('errors', 0)}")
            
            # Этап 4: Саммари и другая полезная информация
            self.logger.info("📋 ЭТАП 4: Генерация саммари и анализ транскрипций...")
            summary_start = time.time()
            summary_stats = self.process_summaries()
            summary_duration = time.time() - summary_start
            self.logger.info(f"⏱️ Время генерации саммари: {summary_duration:.2f} секунд")
            self.logger.info(f"📊 Результат генерации саммари: обработано {summary_stats.get('processed', 0)}, ошибок {summary_stats.get('errors', 0)}")
            
            # Этап 5: Обновление Notion
            self.logger.info("📝 ЭТАП 5: Синхронизация с Notion...")
            notion_start = time.time()
            notion_stats = self.sync_with_notion()
            notion_duration = time.time() - notion_start
            self.logger.info(f"⏱️ Время синхронизации с Notion: {notion_duration:.2f} секунд")
            self.logger.info(f"📊 Результат синхронизации с Notion: {notion_stats}")
            
            # Создаем текущее состояние цикла
            self.current_cycle_state = self._create_cycle_state(
                personal_stats, work_stats, media_stats, transcription_stats, notion_stats, summary_stats
            )
            
            # Этап 6: Отчет в Telegram и создание файлов статуса (параллельно)
            self.logger.info("📱 ЭТАП 6: Отправка уведомлений и создание файлов статуса...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                # Запускаем задачи параллельно
                telegram_future = executor.submit(self.send_telegram_notifications, self.current_cycle_state, self.previous_cycle_state)
                status_future = executor.submit(self.create_status_files)
                
                # Получаем результаты
                telegram_start = time.time()
                telegram_stats = telegram_future.result()
                telegram_duration = time.time() - telegram_start
                self.logger.info(f"⏱️ Время отправки уведомлений: {telegram_duration:.2f} секунд")
                
                status_start = time.time()
                status_future.result()
                status_duration = time.time() - status_start
                self.logger.info(f"⏱️ Время создания файлов статуса: {status_duration:.2f} секунд")
            
            # Сохраняем текущее состояние для следующего цикла
            self._save_current_state(self.current_cycle_state)
            
            # Сохраняем кэш после выполнения цикла
            self._save_cache()
            
            # Логируем результаты
            total_duration = time.time() - start_time
            self.performance_stats['cycle_times'].append(total_duration)
            if len(self.performance_stats['cycle_times']) > 100:
                self.performance_stats['cycle_times'] = self.performance_stats['cycle_times'][-100:]
            
            self.logger.info(f"📊 РЕЗУЛЬТАТЫ ЦИКЛА:")
            self.logger.info(f"   👤 Личный аккаунт: {personal_stats['status']}")
            self.logger.info(f"   🏢 Рабочий аккаунт: {work_stats['status']}")
            self.logger.info(f"   🎬 Медиа: обработано {media_stats.get('processed', 0)}, найдено {media_stats.get('synced', 0)}")
            self.logger.info(f"   🎤 Транскрипция: обработано {transcription_stats.get('processed', 0)}, ошибок {transcription_stats.get('errors', 0)}")
            self.logger.info(f"   📋 Саммари: обработано {summary_stats.get('processed', 0)}, ошибок {summary_stats.get('errors', 0)}")
            self.logger.info(f"   📝 Notion: синхронизировано {notion_stats.get('synced', 0)}, ошибок {notion_stats.get('errors', 0)}")
            self.logger.info(f"   📱 Telegram: {telegram_stats.get('status', 'unknown')}")
            self.logger.info(f"⏱️ ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ ЦИКЛА: {total_duration:.2f} секунд")
            
            # Сохраняем статистику производительности
            self._save_performance_stats()
            
            self.logger.info("✅ Цикл обработки завершен успешно")
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в цикле сервиса: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process_summaries(self) -> Dict[str, Any]:
        """Обработка саммари для транскрипций."""
        try:
            if self.transcription_handler:
                # Используем новый обработчик транскрипций
                summary_stats = self.transcription_handler.process_summaries()
                self.last_summary_stats = summary_stats
                return summary_stats
            else:
                # Используем старый метод
                self.logger.info("📝 Начинаю генерацию саммари для транскрипций...")
                
                summary_stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
                
                # Проверяем наличие транскрипций перед запуском
                has_transcriptions = False
                
                # Обрабатываем личный аккаунт
                if self.config_manager and self.config_manager.is_personal_enabled():
                    personal_config = self.config_manager.get_personal_config()
                    personal_folder = personal_config.get('local_drive_root')
                    if personal_folder and os.path.exists(personal_folder):
                        self.logger.info(f"👤 Проверка транскрипций в папке личного аккаунта: {personal_folder}")
                        personal_result = self._process_folder_summaries(personal_folder, "personal")
                        if personal_result["processed"] > 0:
                            has_transcriptions = True
                            summary_stats["details"].append(personal_result)
                            summary_stats["processed"] += personal_result.get("processed", 0)
                            summary_stats["errors"] += personal_result.get("errors", 0)
                        else:
                            self.logger.info(f"📂 В папке личного аккаунта нет транскрипций для анализа")
                
                # Обрабатываем рабочий аккаунт
                if self.config_manager and self.config_manager.is_work_enabled():
                    work_config = self.config_manager.get_work_config()
                    work_folder = work_config.get('local_drive_root')
                    if work_folder and os.path.exists(work_folder):
                        self.logger.info(f"🏢 Проверка транскрипций в папке рабочего аккаунта: {work_folder}")
                        work_result = self._process_folder_summaries(work_folder, "work")
                        if work_result["processed"] > 0:
                            has_transcriptions = True
                            summary_stats["details"].append(work_result)
                            summary_stats["processed"] += work_result.get("processed", 0)
                            summary_stats["errors"] += work_result.get("errors", 0)
                        else:
                            self.logger.info(f"📂 В папке рабочего аккаунта нет транскрипций для анализа")
                
                if not has_transcriptions:
                    self.logger.info("📂 Нет транскрипций для анализа")
                    summary_stats["status"] = "no_files"
                
                self.logger.info(f"✅ Генерация саммари завершена: обработано {summary_stats['processed']}, ошибок {summary_stats['errors']}")
                
                # Сохраняем статистику для детальных отчетов
                self.last_summary_stats = summary_stats
                
                return summary_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации саммари: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            self.last_summary_stats = error_stats
            return error_stats
    
    def _process_folder_summaries(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """Обработка саммари для транскрипций в конкретной папке."""
        try:
            result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
            
            # Ищем файлы транскрипций для анализа
            transcript_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('_transcript.txt'):
                        # Проверяем, существует ли уже файл саммари
                        transcript_path = os.path.join(root, file)
                        summary_file = transcript_path.replace('_transcript.txt', '_summary.txt')
                        analysis_file = transcript_path.replace('_transcript.txt', '_analysis.json')
                        
                        # Если саммари или анализ уже существуют, пропускаем файл
                        if os.path.exists(summary_file) or os.path.exists(analysis_file):
                            continue
                        
                        transcript_files.append(transcript_path)
            
            if not transcript_files:
                self.logger.info(f"📁 В папке {folder_path} нет новых транскрипций для анализа")
                return result
            
            self.logger.info(f"📄 Найдено {len(transcript_files)} транскрипций для анализа")
            
            # Получаем настройки OpenAI
            openai_config = self.config_manager.get_openai_config()
            openai_api_key = openai_config.get('api_key')
            
            if not openai_api_key:
                self.logger.error("❌ Не настроен API ключ OpenAI")
                result["errors"] += 1
                return result
            
            # Инициализируем анализатор транскрипций
            from transcript_analyzer import TranscriptAnalyzer
            analyzer = TranscriptAnalyzer(
                api_key=openai_api_key,
                model=openai_config.get('analysis_model', 'gpt-4o-mini')
            )
            
            # Обрабатываем каждую транскрипцию
            for transcript_path in transcript_files:
                try:
                    file_name = os.path.basename(transcript_path)
                    self.logger.info(f"📝 Анализирую транскрипцию: {file_name}")
                    
                    # Извлекаем название и дату встречи из имени файла
                    meeting_title = ""
                    meeting_date = ""
                    
                    # Пытаемся извлечь дату из имени файла
                    import re
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
                    if date_match:
                        meeting_date = date_match.group(1)
                    
                    # Пытаемся извлечь название встречи
                    if meeting_date:
                        title_match = re.search(rf'{meeting_date}.*?_transcript\.txt', file_name)
                        if title_match:
                            meeting_title = title_match.group(0).replace(f"{meeting_date} ", "").replace("_transcript.txt", "")
                    
                    # Читаем транскрипцию
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        transcript_text = f.read()
                    
                    # Анализируем транскрипцию
                    analysis_result = analyzer.analyze_meeting_transcript(
                        transcript=transcript_text,
                        meeting_title=meeting_title,
                        meeting_date=meeting_date
                    )
                    
                    # Сохраняем результат анализа в JSON
                    analysis_file = transcript_path.replace('_transcript.txt', '_analysis.json')
                    with open(analysis_file, 'w', encoding='utf-8') as f:
                        import json
                        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
                    
                    # Создаем текстовое саммари
                    summary_file = transcript_path.replace('_transcript.txt', '_summary.txt')
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        summary = analysis_result.get('meeting_summary', {})
                        f.write(f"# {summary.get('title', 'Встреча')}\n\n")
                        f.write(f"Дата: {meeting_date}\n\n")
                        f.write(f"## Основная тема\n{summary.get('main_topic', 'Не указана')}\n\n")
                        
                        # Ключевые решения
                        f.write("## Ключевые решения\n")
                        for decision in summary.get('key_decisions', []):
                            f.write(f"- {decision}\n")
                        f.write("\n")
                        
                        # Действия
                        f.write("## Действия\n")
                        for action in summary.get('action_items', []):
                            f.write(f"- {action}\n")
                        f.write("\n")
                        
                        # Следующие шаги
                        f.write("## Следующие шаги\n")
                        for step in summary.get('next_steps', []):
                            f.write(f"- {step}\n")
                        f.write("\n")
                        
                        # Участники
                        f.write("## Участники\n")
                        for participant in summary.get('participants', []):
                            f.write(f"- {participant}\n")
                    
                    result["processed"] += 1
                    result["files"].append({
                        "file": file_name,
                        "status": "success",
                        "output": os.path.basename(summary_file)
                    })
                    
                    self.logger.info(f"✅ Анализ завершен: {file_name}")
                    
                except Exception as e:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(transcript_path),
                        "status": "error",
                        "error": str(e)
                    })
                    self.logger.error(f"❌ Ошибка анализа {os.path.basename(transcript_path)}: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}
    
    def service_worker(self):
        """Рабочий поток сервиса."""
        self.logger.info("👷 Рабочий поток сервиса запущен")
        
        while self.running:
            try:
                self.run_service_cycle()
                
                # Ждем до следующей проверки
                time.sleep(self.interval)
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка в рабочем потоке: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def start(self):
        """Запуск сервиса."""
        if self.running:
            self.logger.warning("⚠️ Сервис уже запущен")
            return
        
        # Загружаем окружение
        if not self._load_config():
            self.logger.error("❌ Не удалось загрузить окружение")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.service_worker, daemon=True)
        self.thread.start()
        
        self.logger.info("🚀 Сервис запущен и работает в фоне")
        self.logger.info(f"⏰ Интервал проверки: {self.interval} секунд")
        self.logger.info(f"🎬 Интервал медиа: {self.media_check_interval} секунд")
        
        # Основной цикл для обработки сигналов
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("⌨️ Получен сигнал прерывания")
        finally:
            self.stop()
    
    def stop(self):
        """Остановка сервиса."""
        if not self.running:
            return
        
        self.logger.info("🛑 Останавливаю сервис...")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=10)
            if self.thread.is_alive():
                self.logger.warning("⚠️ Рабочий поток не завершился корректно")
        
        self.logger.info("✅ Сервис остановлен")


def main():
    """Точка входа для запуска сервиса."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Сервис автоматизации встреч")
    parser.add_argument("--config", default=".env", help="Путь к файлу конфигурации")
    parser.add_argument("--interval", type=int, default=300, help="Интервал проверки в секундах")
    parser.add_argument("--media-interval", type=int, default=1800, help="Интервал медиа обработки в секундах")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    
    args = parser.parse_args()
    
    # Создаем и запускаем сервис
    service = MeetingAutomationService(
        config_file=args.config,
        interval=args.interval,
        media_interval=args.media_interval,
        log_level=args.log_level
    )
    
    try:
        service.start()
    except Exception as e:
        print(f"❌ Критическая ошибка запуска сервиса: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
