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
import uuid
from logging.handlers import RotatingFileHandler
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



# Импортируем новые модульные обработчики
try:
    from src.handlers import (
        CalendarHandler,
        CalendarIntegrationHandler,
        AccountHandler,
        TranscriptionHandler,
        SummaryHandler,
        MediaHandler,
        NotionHandler,
        MetricsHandler
    )
    from src.handlers.smart_report_generator import SmartReportGenerator
    from src.handlers.state_manager import StateManager
    NEW_HANDLERS_AVAILABLE = True
    print("✅ Новые модульные обработчики загружены")
except ImportError as e:
    print(f"❌ Критическая ошибка: новые обработчики недоступны: {e}")
    print("Система не может работать без модульных обработчиков")
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
        if not self._load_config():
            raise RuntimeError("Не удалось загрузить конфигурацию")
        
        # Инициализируем переменные для хранения статистики
        self.last_media_check = 0
        self.last_media_stats = {}
        self.last_transcription_stats = {}
        self.last_notion_stats = {}
        self.last_telegram_stats = {}
        self.last_summary_stats = {}
        self.last_notion_update_stats = {}
        
        # Инициализируем переменные для хранения состояния
        self.previous_cycle_state = {}
        self.current_cycle_state = {}
        self.cycle_counter = 0  # Счетчик выполненных циклов
        
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
            # Создаем экземпляры новых модульных обработчиков
            # Сначала создаем notion_handler
            self.notion_handler = NotionHandler(self.config_manager, None, self.logger)
            
            # Сначала создаем notion_handler
            self.notion_handler = NotionHandler(self.config_manager, None, self.logger)
            
            # Затем создаем account_handler с notion_handler
            self.account_handler = AccountHandler(self.config_manager, None, self.notion_handler, self.logger)
            self.transcription_handler_new = TranscriptionHandler(self.config_manager, None, self.logger)
            self.summary_handler = SummaryHandler(self.config_manager, None, self.logger)
            # Передаем self (ServiceManager) в MediaHandler для доступа к кэшу
            self.media_handler = MediaHandler(self.config_manager, None, self.logger, service_manager=self)
            self.calendar_handler = CalendarHandler(self.config_manager, self.logger)
            self.logger.info(f"📅 CalendarHandler создан: {type(self.calendar_handler).__name__}")
            
            self.calendar_integration_handler = CalendarIntegrationHandler(self.config_manager, self.notion_handler, self.calendar_handler, self.logger)
            self.logger.info(f"📅 CalendarIntegrationHandler создан с calendar_handler: {type(self.calendar_integration_handler.calendar_handler).__name__}")
            self.metrics_handler = MetricsHandler(self.config_manager, self.logger)
            self.smart_report_generator = SmartReportGenerator(self.logger)
            self.state_manager = StateManager(logger=self.logger)
            self.logger.info("✅ SmartReportGenerator инициализирован")
            self.logger.info("✅ StateManager инициализирован")
            self.logger.info("✅ CalendarHandler инициализирован")
            self.logger.info("✅ CalendarIntegrationHandler инициализирован")
            
            self.logger.info("✅ Все модульные обработчики инициализированы")
                
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка инициализации обработчиков: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            raise
    
    def _setup_logging(self, log_level: str) -> logging.Logger:
        """Настройка логирования."""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # РАДИКАЛЬНОЕ РЕШЕНИЕ: Создаем НОВЫЙ логгер каждый раз
        # Это гарантирует отсутствие дублирующих хендлеров
        logger_name = f"meeting_automation_service_{id(self)}"
        logger = logging.getLogger(logger_name)
        
        # Сбрасываем уровень и propagate
        logger.setLevel(logging.getLevelName(log_level))
        logger.propagate = False
        
        # ПРИНУДИТЕЛЬНО очищаем ВСЕ существующие хендлеры
        while logger.handlers:
            logger.removeHandler(logger.handlers[0])
        
        # Дополнительно: очищаем ВСЕ логгеры с похожими именами
        for existing_logger_name in logging.root.manager.loggerDict:
            if existing_logger_name.startswith("meeting_automation_service"):
                existing_logger = logging.getLogger(existing_logger_name)
                while existing_logger.handlers:
                    existing_logger.removeHandler(existing_logger.handlers[0])
                print(f"🧹 Очищен логгер: {existing_logger_name}")
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Хендлер для основного лога (INFO и выше)
        # Настройки ротации логов
        max_bytes = int(os.getenv("LOG_MAX_SIZE_MB", "100")) * 1024 * 1024
        backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        
        # ФИНАЛЬНОЕ РЕШЕНИЕ: Используем ТОЛЬКО файловый хендлер
        # Это предотвращает дублирование логов
        file_handler = RotatingFileHandler(
            log_dir / "service.log",
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Добавляем ТОЛЬКО файловый хендлер
        logger.addHandler(file_handler)
        
        # КОНСОЛЬНЫЙ ХЕНДЛЕР ОТКЛЮЧЕН для предотвращения дублирования
        # console_handler = logging.StreamHandler()
        # console_handler.setLevel(logging.INFO)
        # console_handler.setFormatter(formatter)
        # logger.addHandler(console_handler)
        
        # Диагностика: проверяем количество хендлеров
        print(f"🔍 Логгер '{logger.name}' настроен с {len(logger.handlers)} хендлерами")
        print(f"🔍 ID логгера: {id(logger)}")
        
        # Дополнительная диагностика: проверяем хендлеры
        for i, handler in enumerate(logger.handlers):
            print(f"🔍 Хендлер {i}: {type(handler).__name__}")
        
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
                self.config_manager = ConfigManager()
                
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
            return self.account_handler.process_account('personal')
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки личного аккаунта: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "output": str(e)}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def run_work_automation(self) -> Dict[str, Any]:
        """Запуск автоматизации для рабочего аккаунта."""
        try:
            return self.account_handler.process_account('work')
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
            
            # Используем новый модульный обработчик
            media_stats = self.media_handler.process('medium')
            self.last_media_stats = media_stats
            return media_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки медиа: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {"status": "error", "processed": 0, "synced": 0, "cleanup": 0, "errors": 1}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process_audio_transcription(self) -> Dict[str, Any]:
        """Обработка транскрипции аудио файлов."""
        try:
            transcription_stats = self.transcription_handler_new.process()
            self.last_transcription_stats = transcription_stats
            return transcription_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка транскрипции: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            self.last_transcription_stats = error_stats
            return error_stats
    

    
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
    
    def _has_changes(self, current_state: Dict[str, Any], previous_state: Dict[str, Any]) -> bool:
        """
        Проверка наличия изменений в состоянии системы.
        
        Args:
            current_state: Текущее состояние
            previous_state: Предыдущее состояние
            
        Returns:
            True если есть изменения, False если изменений нет
        """
        try:
            self.logger.info(f"🔍 Проверка изменений: previous_state={bool(previous_state)}")
            
            if not previous_state:
                # Если предыдущее состояние отсутствует, проверяем есть ли реальные изменения
                # в текущем состоянии (обработанные события, ошибки, etc.)
                personal_processed = current_state.get('personal_events', {}).get('processed', 0)
                work_processed = current_state.get('work_events', {}).get('processed', 0)
                media_processed = current_state.get('media_processed', {}).get('count', 0)
                transcriptions = current_state.get('transcriptions', {}).get('count', 0)
                notion_synced = current_state.get('notion_synced', {}).get('count', 0)
                errors_count = current_state.get('errors_count', 0)
                
                self.logger.info(f"🔍 Метрики без предыдущего состояния: personal={personal_processed}, work={work_processed}, media={media_processed}, transcriptions={transcriptions}, notion={notion_synced}, errors={errors_count}")
                
                # Если есть реальные изменения, считаем что есть изменения
                if (personal_processed > 0 or work_processed > 0 or 
                    media_processed > 0 or transcriptions > 0 or 
                    notion_synced > 0 or errors_count > 0):
                    self.logger.info("🔍 Предыдущее состояние отсутствует, но есть реальные изменения")
                    return True
                else:
                    self.logger.info("🔍 Предыдущее состояние отсутствует, реальных изменений нет")
                    return False
            
            # Проверяем изменения в ключевых метриках
            current_metrics = {
                'personal_events': current_state.get('personal_events', {}).get('processed', 0),
                'work_events': current_state.get('work_events', {}).get('processed', 0),
                'media_processed': current_state.get('media_processed', {}).get('count', 0),
                'transcriptions': current_state.get('transcriptions', {}).get('count', 0),
                'notion_synced': current_state.get('notion_synced', {}).get('count', 0),
                'errors_count': current_state.get('errors_count', 0)
            }
            
            previous_metrics = {
                'personal_events': previous_state.get('personal_events', {}).get('processed', 0),
                'work_events': previous_state.get('work_events', {}).get('processed', 0),
                'media_processed': previous_state.get('media_processed', {}).get('count', 0),
                'transcriptions': previous_state.get('transcriptions', {}).get('count', 0),
                'notion_synced': previous_state.get('notion_synced', {}).get('count', 0),
                'errors_count': previous_state.get('errors_count', 0)
            }
            
            self.logger.info(f"🔍 Сравнение метрик: current={current_metrics}, previous={previous_metrics}")
            
            # Проверяем изменения в метриках (только увеличение или новые ошибки)
            for key in current_metrics:
                if current_metrics[key] != previous_metrics[key]:
                    # Считаем изменением только увеличение метрик или появление новых ошибок
                    if current_metrics[key] > previous_metrics[key]:
                        self.logger.info(f"🔍 Обнаружены изменения в {key}: {previous_metrics[key]} -> {current_metrics[key]}")
                        return True
                    elif key == 'errors_count' and current_metrics[key] > 0:
                        # Ошибки всегда считаем изменением
                        self.logger.info(f"🔍 Обнаружены ошибки в {key}: {previous_metrics[key]} -> {current_metrics[key]}")
                        return True
                    else:
                        # Снижение метрик не считаем изменением (кроме ошибок)
                        self.logger.debug(f"🔍 Снижение метрики {key}: {previous_metrics[key]} -> {current_metrics[key]} (не считается изменением)")
            
            # Проверяем изменения в статусах
            current_statuses = {
                'personal_status': current_state.get('personal_events', {}).get('status', ''),
                'work_status': current_state.get('work_events', {}).get('status', ''),
                'media_status': current_state.get('media_processed', {}).get('status', ''),
                'transcription_status': current_state.get('transcriptions', {}).get('status', ''),
                'notion_status': current_state.get('notion_synced', {}).get('status', '')
            }
            
            previous_statuses = {
                'personal_status': previous_state.get('personal_events', {}).get('status', ''),
                'work_status': previous_state.get('work_events', {}).get('status', ''),
                'media_status': previous_state.get('media_processed', {}).get('status', ''),
                'transcription_status': previous_state.get('transcriptions', {}).get('status', ''),
                'notion_status': previous_state.get('notion_synced', {}).get('status', '')
            }
            
            self.logger.info(f"🔍 Сравнение статусов: current={current_statuses}, previous={previous_statuses}")
            
            for key in current_statuses:
                if current_statuses[key] != previous_statuses[key]:
                    # Считаем изменением только переход к статусу 'error' или от 'error' к другому статусу
                    if (current_statuses[key] == 'error' or 
                        (previous_statuses[key] == 'error' and current_statuses[key] != 'error')):
                        self.logger.info(f"🔍 Обнаружены изменения в статусе {key}: {previous_statuses[key]} -> {current_statuses[key]}")
                        return True
                    else:
                        # Остальные изменения статусов не считаем значимыми
                        self.logger.debug(f"🔍 Изменение статуса {key}: {previous_statuses[key]} -> {current_statuses[key]} (не считается изменением)")
            
            # Проверяем изменения во времени последнего обновления (только если время не пустое)
            current_time = current_state.get('last_update', '')
            previous_time = previous_state.get('last_update', '')
            
            if current_time != previous_time and current_time and previous_time:
                self.logger.info(f"🔍 Обнаружены изменения во времени: {previous_time} -> {current_time}")
                return True
            elif current_time != previous_time:
                # Если одно из времен пустое, не считаем это изменением
                self.logger.debug(f"🔍 Изменение времени (пустое): {previous_time} -> {current_time} (не считается изменением)")
            
            # Проверяем, есть ли новые события (даже если они не были обработаны)
            personal_new = current_state.get('personal_events', {}).get('new', 0)
            work_new = current_state.get('work_events', {}).get('new', 0)
            
            if personal_new > 0 or work_new > 0:
                self.logger.info(f"🔍 Обнаружены новые события: личный {personal_new}, рабочий {work_new}")
                return True
            
            self.logger.info("🔍 Изменений не обнаружено")
            return False
            
        except Exception as e:
            self.logger.warning(f"⚠️ Ошибка проверки изменений: {e}")
            return True  # В случае ошибки считаем что есть изменения
    
    def _format_detailed_report(self, current_state: Dict[str, Any] = None) -> str:
        """Формирование детального отчета для Telegram."""
        try:
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report = f"🤖 <b>Отчет системы автоматизации встреч</b>\n\n"
            report += f"⏰ <b>Время выполнения:</b> {current_time}\n"
            report += f"🔄 <b>Цикл:</b> #{current_state.get('cycle_number', 'N/A') if current_state else 'N/A'}\n\n"
            
            # Добавляем информацию о статусе аккаунтов
            if self.config_manager:
                report += "📋 <b>Статус аккаунтов:</b>\n"
                if self.config_manager.is_personal_enabled():
                    report += "   👤 <b>Личный аккаунт:</b> ✅ Активен\n"
                else:
                    report += "   👤 <b>Личный аккаунт:</b> ❌ Отключен\n"
                
                if self.config_manager.is_work_enabled():
                    report += "   🏢 <b>Рабочий аккаунт:</b> ✅ Активен\n"
                else:
                    report += "   🏢 <b>Рабочий аккаунт:</b> ❌ Отключен\n"
            
            # Добавляем детальную информацию о том, что отработано
            if current_state:
                report += "\n📊 <b>Результаты выполнения:</b>\n"
                
                # Календарные события
                personal_events = current_state.get('personal_events', {})
                work_events = current_state.get('work_events', {})
                
                report += "📅 <b>Календарные события:</b>\n"
                if personal_events.get('status') == 'success':
                    processed = personal_events.get('processed', 0)
                    total = personal_events.get('total', 0)
                    new = personal_events.get('new', 0)
                    already_processed = personal_events.get('already_processed', 0)
                    
                    if processed > 0:
                        report += f"   👤 <b>Личный календарь:</b> ✅ Обработано {processed} новых событий\n"
                        report += f"      📊 Всего событий: {total}, уже обработано: {already_processed}\n"
                    elif new > 0:
                        report += f"   👤 <b>Личный календарь:</b> ⏭️ {new} новых событий (требуют обработки)\n"
                        report += f"      📊 Всего событий: {total}, уже обработано: {already_processed}\n"
                    else:
                        report += f"   👤 <b>Личный календарь:</b> ⏭️ Новых событий нет\n"
                        # Показываем статистику только если есть события
                        if total > 0:
                            report += f"      📊 Всего событий: {total}\n"
                else:
                    report += f"   👤 <b>Личный календарь:</b> ❌ {personal_events.get('message', 'Ошибка')}\n"
                
                if work_events.get('status') == 'success':
                    processed = work_events.get('processed', 0)
                    total = work_events.get('total', 0)
                    new = work_events.get('new', 0)
                    already_processed = work_events.get('already_processed', 0)
                    
                    if processed > 0:
                        report += f"   🏢 <b>Рабочий календарь:</b> ✅ Обработано {processed} новых событий\n"
                        report += f"      📊 Всего событий: {total}, уже обработано: {already_processed}\n"
                    elif new > 0:
                        report += f"   🏢 <b>Рабочий календарь:</b> ⏭️ {new} новых событий (требуют обработки)\n"
                        report += f"      📊 Всего событий: {total}, уже обработано: {already_processed}\n"
                    else:
                        report += f"   🏢 <b>Рабочий календарь:</b> ⏭️ Новых событий нет\n"
                        # Показываем статистику только если есть события
                        if total > 0:
                            report += f"      📊 Всего событий: {total}\n"
                else:
                    report += f"   🏢 <b>Рабочий календарь:</b> ❌ {work_events.get('message', 'Ошибка')}\n"
                
                # Медиа файлы
                media_processed = current_state.get('media_processed', {})
                report += "\n🎬 <b>Медиа файлы:</b>\n"
                if media_processed.get('count', 0) > 0:
                    report += f"   ✅ Обработано {media_processed.get('count', 0)} файлов\n"
                    if media_processed.get('total_size'):
                        report += f"   📏 Общий размер: {media_processed.get('total_size', 'N/A')}\n"
                else:
                    report += "   ⏭️ Новых файлов нет\n"
                
                # Транскрипции
                transcriptions = current_state.get('transcriptions', {})
                report += "\n🎤 <b>Транскрипции:</b>\n"
                if transcriptions.get('count', 0) > 0:
                    report += f"   ✅ Обработано {transcriptions.get('count', 0)} файлов\n"
                    if transcriptions.get('total_duration'):
                        report += f"   ⏱️ Общая длительность: {transcriptions.get('total_duration', 'N/A')}\n"
                else:
                    report += "   ⏭️ Новых файлов нет\n"
                
                # Notion синхронизация
                notion_synced = current_state.get('notion_synced', {})
                report += "\n📝 <b>Notion синхронизация:</b>\n"
                if notion_synced.get('count', 0) > 0:
                    report += f"   ✅ Синхронизировано {notion_synced.get('count', 0)} страниц\n"
                    if notion_synced.get('updated'):
                        report += f"   🔄 Обновлено: {notion_synced.get('updated', 0)} страниц\n"
                else:
                    report += "   ⏭️ Новых страниц нет\n"
                
                # Время выполнения
                execution_time = current_state.get('execution_time', 0)
                if execution_time > 0:
                    report += f"\n⏱️ <b>Время выполнения цикла:</b> {execution_time:.2f} секунд\n"
                
                # Ошибки
                errors_count = current_state.get('errors_count', 0)
                if errors_count > 0:
                    report += f"\n⚠️ <b>Ошибки:</b> {errors_count} ошибок\n"
                
                # Статистика по папкам
                folders_processed = current_state.get('folders_processed', {})
                if folders_processed:
                    report += f"\n📁 <b>Папки:</b> Обработано {folders_processed.get('count', 0)} папок\n"
                
                # Добавляем детальную информацию об ошибках, если есть
                if errors_count > 0:
                    report += "\n🔍 <b>Детали ошибок:</b>\n"
                    report += "```\n"
                    
                    # Собираем все ошибки из компонентов
                    error_details = []
                    
                    # Ошибки календаря
                    personal_errors = personal_events.get('errors', [])
                    work_errors = work_events.get('errors', [])
                    if personal_errors:
                        error_details.extend([f"Личный календарь: {error}" for error in personal_errors])
                    if work_errors:
                        error_details.extend([f"Рабочий календарь: {error}" for error in work_errors])
                    
                    # Ошибки медиа
                    media_errors = media_processed.get('errors', [])
                    if media_errors:
                        error_details.extend([f"Медиа: {error}" for error in media_errors])
                    
                    # Ошибки транскрипции
                    transcription_errors = transcriptions.get('errors', [])
                    if transcription_errors:
                        error_details.extend([f"Транскрипция: {error}" for error in transcription_errors])
                    
                    # Ошибки Notion
                    notion_errors = notion_synced.get('errors', [])
                    if notion_errors:
                        error_details.extend([f"Notion: {error}" for error in notion_errors])
                    
                    # Если есть детальные ошибки, показываем их
                    if error_details:
                        for error in error_details[:5]:  # Показываем первые 5 ошибок
                            report += f"{error}\n"
                    else:
                        report += "Общие ошибки системы\n"
                    
                    report += "```\n"
            
            report += "\n🎯 <b>Статус:</b> "
            if current_state and current_state.get('errors_count', 0) == 0:
                report += "✅ Система работает в штатном режиме"
            else:
                report += "⚠️ Обнаружены ошибки в работе"
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка формирования детального отчета: {e}")
            return f"❌ Ошибка формирования отчета: {str(e)}"
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def send_telegram_notifications(self, current_state: Dict[str, Any], previous_state: Dict[str, Any]) -> Dict[str, Any]:
        """Отправка уведомлений в Telegram."""
        try:
            self.logger.info("📱 Проверка необходимости отправки уведомлений в Telegram...")
            
            # Проверяем, нужно ли отправлять уведомление
            # 🔧 ИСПРАВЛЕНО: Логика проверки изменений
            import os
            force_send = os.getenv('TELEGRAM_ALWAYS_SEND', 'false').lower() == 'true'
            self.logger.info(f"📱 TELEGRAM_ALWAYS_SEND: {force_send}")
            
            if not force_send:
                self.logger.info("📱 Проверяю наличие изменений через StateManager...")
                has_changes = self.state_manager.has_changes(current_state)
                self.logger.info(f"📱 Результат проверки изменений: {has_changes}")
                
                if not has_changes:
                    self.logger.info("⏭️ Нет изменений, пропускаю отправку уведомлений")
                    return {"status": "skipped", "message": "No changes detected"}
                else:
                    self.logger.info("📱 Обнаружены изменения, отправляю отчет")
            else:
                self.logger.info("📱 Принудительная отправка включена")
            
            # Формируем умный отчет через SmartReportGenerator
            self.logger.info("🔍 Использую SmartReportGenerator для формирования отчета...")
            try:
                report = self.smart_report_generator.generate_smart_report(
                    current_state, previous_state, 
                    current_state.get('execution_time', 0) if current_state else 0
                )
                self.logger.info(f"🔍 SmartReportGenerator вернул: {type(report)}, длина: {len(report) if report else 0}")
            except Exception as e:
                self.logger.error(f"❌ Ошибка в SmartReportGenerator: {e}")
                self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
                report = None
            
            # Если отчет не сгенерирован (нет изменений), пропускаем отправку
            if not report:
                self.logger.info("⏭️ SmartReportGenerator не обнаружил изменений, пропускаю отправку")
                return {"status": "skipped", "message": "No changes detected by SmartReportGenerator"}
            
            # Отправляем уведомление с правильным типом
            self.logger.info("📱 Отправка детального отчета в Telegram...")
            self.logger.info(f"🔍 Содержимое отчета (первые 200 символов): {report[:200]}...")
            self.logger.info(f"🔍 Полный отчет: {report}")
            
            cmd = [
                sys.executable,
                'meeting_automation_universal.py',
                'notify',
                '--message', report,
                '--notification_type', 'detailed'
            ]
            
            self.logger.info(f"🔄 Запуск команды: {' '.join(cmd[:4])}...")
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            # Логируем результат выполнения команды
            self.logger.info(f"🔍 Команда выполнена: returncode={process.returncode}")
            if process.stdout:
                self.logger.info(f"🔍 stdout: {process.stdout}")
            if process.stderr:
                self.logger.info(f"🔍 stderr: {process.stderr}")
            
            if process.returncode == 0:
                self.logger.info("✅ Детальный отчет отправлен в Telegram успешно")
                return {"status": "success", "message": "Detailed report sent"}
            else:
                self.logger.error(f"❌ Ошибка отправки детального отчета: {process.stderr}")
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
                self.logger.info(f"🔍 Личный аккаунт: папка = {personal_folder}, существует = {os.path.exists(personal_folder) if personal_folder else False}")
                if personal_folder and os.path.exists(personal_folder):
                    # Создаем статус в корневой папке
                    self._create_folder_status_file(personal_folder, "personal")
                    # Создаем статус в каждой папке встречи
                    self._create_meeting_status_files(personal_folder, "personal")
                else:
                    self.logger.warning(f"⚠️ Папка личного аккаунта недоступна: {personal_folder}")
            
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                self.logger.info(f"🔍 Рабочий аккаунт: папка = {work_folder}, существует = {os.path.exists(work_folder) if work_folder else False}")
                if work_folder and os.path.exists(work_folder):
                    # Создаем статус в корневой папке
                    self._create_folder_status_file(work_folder, "work")
                    # Создаем статус в каждой папке встречи
                    self._create_meeting_status_files(work_folder, "work")
                else:
                    self.logger.warning(f"⚠️ Папка рабочего аккаунта недоступна: {work_folder}")
            
            self.logger.info("✅ Файлы статуса созданы")
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания файлов статуса: {e}")
    
    def _create_folder_status_file(self, folder_path: str, account_type: str):
        """Создание файла статуса для конкретной папки."""
        try:
            status_file_path = os.path.join(folder_path, "processing_status.md")
            
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
            # Увеличиваем счетчик циклов
            self.cycle_counter += 1
            
            # Засекаем время начала цикла
            self._cycle_start_time = time.time()
            
            # ДИАГНОСТИКА: проверяем количество хендлеров
            print(f"🔍 Цикл #{self.cycle_counter}: логгер '{self.logger.name}' имеет {len(self.logger.handlers)} хендлеров")
            
            start_time = time.time()
            self.logger.info(f"🔄 Запуск цикла обработки #{self.cycle_counter}...")
            self.logger.info(f"⏰ Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Мониторинг производительности в начале цикла
            self._monitor_performance()
            
            # Загружаем предыдущее состояние
            self.previous_cycle_state = self._load_previous_state()
            
            # Обновляем кэш перед запуском цикла
            self._load_cache()
            
            # Этап 1: Календарь → создание папок встреч и страниц Notion
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
            
            # Этап 4: Саммари и другая полезная информация (если включено)
            summary_config = self.config_manager.get_summary_config()
            if summary_config.get('enable_general_summary', False) or summary_config.get('enable_complex_summary', False):
                self.logger.info("📋 ЭТАП 4: Генерация саммари и анализ транскрипций...")
                summary_start = time.time()
                summary_stats, notion_update_stats = self.process_summaries()
                summary_duration = time.time() - summary_start
                self.logger.info(f"⏱️ Время генерации саммари: {summary_duration:.2f} секунд")
                self.logger.info(f"📊 Результат генерации саммари: обработано {summary_stats.get('processed', 0)}, ошибок {summary_stats.get('errors', 0)}")
            else:
                self.logger.info("📋 ЭТАП 4: Генерация саммари отключена в настройках")
                summary_stats = {"status": "skipped", "processed": 0, "errors": 0, "message": "General summary disabled"}
                notion_update_stats = {"status": "skipped", "message": "Notion updates not implemented"}
            
            # Этап 5: Обновление Notion
            self.logger.info("📝 ЭТАП 5: Синхронизация с Notion...")
            notion_start = time.time()
            notion_stats = self.sync_with_notion()
            notion_duration = time.time() - notion_start
            self.logger.info(f"⏱️ Время синхронизации с Notion: {notion_duration:.2f} секунд")
            self.logger.info(f"📊 Результат синхронизации с Notion: {notion_stats}")
            
            # Этап 5.5: Обновление страниц Notion результатами обработки
            self.logger.info("📝 ЭТАП 5.5: Обновление страниц Notion результатами обработки...")
            notion_update_start = time.time()
            notion_update_stats = self._update_notion_with_results()
            notion_update_duration = time.time() - notion_update_start
            self.logger.info(f"⏱️ Время обновления страниц Notion: {notion_update_duration:.2f} секунд")
            self.logger.info(f"📊 Результат обновления страниц Notion: {notion_update_stats}")
            
            # Создаем текущее состояние цикла
            self.current_cycle_state = self._create_cycle_state(
                personal_stats, work_stats, media_stats, transcription_stats, notion_stats, summary_stats, notion_update_stats
            )
            
            # Сохраняем текущее состояние в SQLite
            cycle_id = getattr(self, 'cycle_count', 0) + 1
            self.state_manager.save_system_state(self.current_cycle_state, cycle_id)
            self.cycle_count = cycle_id
            
            # Сохраняем текущее состояние (старый метод для совместимости)
            self._save_state(self.current_cycle_state)
            
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
            self._save_state(self.current_cycle_state)
            
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
    def process_summaries(self) -> tuple:
        """Обработка саммари для транскрипций."""
        try:
            summary_stats, notion_update_stats = self.summary_handler.process()
            self.last_summary_stats = summary_stats
            return summary_stats, notion_update_stats
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации саммари: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            self.last_summary_stats = error_stats
            return error_stats, {"status": "skipped", "message": "Notion updates not implemented"}
    

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
    
    def _load_previous_state(self):
        """Загрузка предыдущего состояния сервиса."""
        try:
            state_file = Path('data/service_state.json')
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                self.logger.info(f"✅ Предыдущее состояние загружено из {state_file}")
                return state
            else:
                self.logger.info("⚠️ Файл состояния не найден, используем пустое состояние")
                return {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки состояния: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            return {}
    
    def _create_cycle_state(self, personal_stats, work_stats, media_stats, transcription_stats, notion_stats, summary_stats, notion_update_stats):
        """Создание состояния текущего цикла обработки."""
        try:
            # Вычисляем общее время выполнения
            total_time = time.time() - getattr(self, '_cycle_start_time', time.time())
            
            # Создаем детальное состояние цикла
            cycle_state = {
                "timestamp": datetime.now().isoformat(),
                "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cycle_number": self.cycle_counter,
                "cycle_id": str(uuid.uuid4()),
                "execution_time": round(total_time, 2),
                
                # Статистика по аккаунтам
                "personal_events": {
                    "status": personal_stats.get("status", "skipped"),
                    "processed": personal_stats.get("processed", 0),
                    "total": personal_stats.get("total", 0),
                    "new": personal_stats.get("new", 0),
                    "already_processed": personal_stats.get("already_processed", 0),
                    "message": personal_stats.get("message", ""),
                    "duration": personal_stats.get("duration", 0),
                    "errors": personal_stats.get("errors", 0)
                },
                "work_events": {
                    "status": work_stats.get("status", "skipped"),
                    "processed": work_stats.get("processed", 0),
                    "total": work_stats.get("total", 0),
                    "new": work_stats.get("new", 0),
                    "already_processed": work_stats.get("already_processed", 0),
                    "message": work_stats.get("message", ""),
                    "duration": work_stats.get("duration", 0),
                    "errors": work_stats.get("errors", 0)
                },
                
                # Статистика по медиа
                "media_processed": {
                    "status": media_stats.get("status", "skipped"),
                    "count": media_stats.get("processed", 0),
                    "total_size": media_stats.get("total_size", "N/A"),
                    "duration": media_stats.get("duration", 0),
                    "message": media_stats.get("message", ""),
                    "errors": media_stats.get("errors", 0)
                },
                
                # Статистика по транскрипциям
                "transcriptions": {
                    "status": transcription_stats.get("status", "skipped"),
                    "count": transcription_stats.get("processed", 0),
                    "total_duration": transcription_stats.get("total_duration", "N/A"),
                    "duration": transcription_stats.get("duration", 0),
                    "errors": transcription_stats.get("errors", 0),
                    "message": transcription_stats.get("message", "")
                },
                
                # Статистика по Notion
                "notion_synced": {
                    "status": notion_stats.get("status", "skipped"),
                    "count": notion_stats.get("processed", 0),
                    "updated": notion_stats.get("updated", 0),
                    "duration": notion_stats.get("duration", 0),
                    "message": notion_stats.get("message", ""),
                    "errors": notion_stats.get("errors", 0)
                },
                
                # Статистика по саммари
                "summaries": {
                    "status": summary_stats.get("status", "skipped"),
                    "count": summary_stats.get("processed", 0),
                    "errors": summary_stats.get("errors", 0),
                    "duration": summary_stats.get("duration", 0),
                    "message": summary_stats.get("message", "")
                },
                
                # Общая статистика
                "total_processed": (
                    personal_stats.get("processed", 0) + 
                    work_stats.get("processed", 0) + 
                    media_stats.get("processed", 0) + 
                    transcription_stats.get("processed", 0) + 
                    notion_stats.get("processed", 0) + 
                    summary_stats.get("processed", 0) + 
                    notion_update_stats.get("processed", 0)
                ),
                "errors_count": (
                    personal_stats.get("errors", 0) + 
                    work_stats.get("errors", 0) + 
                    media_stats.get("errors", 0) + 
                    transcription_stats.get("errors", 0) + 
                    notion_stats.get("errors", 0) + 
                    summary_stats.get("errors", 0) + 
                    notion_update_stats.get("errors", 0)
                ),
                
                "status": "completed"
            }
            
            self.logger.debug(f"📊 Создано состояние цикла #{self.cycle_counter}: {cycle_state}")
            return cycle_state
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка создания состояния цикла: {e}")
            # Возвращаем базовое состояние в случае ошибки
            return {
                "timestamp": datetime.now().isoformat(),
                "cycle_number": self.cycle_counter,
                "status": "error",
                "error": str(e)
            }

    def _save_state(self, state):
        """Сохранение состояния цикла."""
        try:
            # TODO: Реализовать сохранение состояния
            pass
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения состояния: {e}")
    @retry(max_attempts=2, delay=3, backoff=2)
    def _update_notion_with_results(self) -> Dict[str, Any]:
        """Обновляет страницы Notion результатами обработки."""
        try:
            self.logger.info("📝 Запуск обновления страниц Notion результатами обработки...")
            start_time = time.time()
            
            # Получаем результаты обработки из текущего состояния
            # Пока используем заглушки, так как конкретная реализация обновления Notion не реализована
            processed_files = []  # TODO: Получить из кэша или состояния
            transcribed_files = []  # TODO: Получить из кэша или состояния
            summarized_files = []  # TODO: Получить из кэша или состояния
            
            update_stats = {
                "status": "success",
                "processed": len(processed_files),
                "updated": 0,
                "duration": 0,
                "message": "Notion pages updated successfully",
                "errors": 0
            }
            
            # TODO: Реализовать обновление конкретных страниц Notion
            # Пока просто логируем статистику
            self.logger.info(f"📊 Статистика для обновления Notion: {len(processed_files)} обработано, {len(transcribed_files)} транскрибировано, {len(summarized_files)} саммари")
            
            duration = time.time() - start_time
            update_stats["duration"] = duration
            
            self.logger.info(f"📝 Обновление страниц Notion завершено за {duration:.2f} секунд")
            return update_stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обновления страниц Notion: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")
            error_stats = {
                "status": "error",
                "processed": 0,
                "updated": 0,
                "duration": 0,
                "message": str(e),
                "errors": 1
            }
            return error_stats
        """Сохранение состояния сервиса."""
        try:
            # Создаем директорию для состояния, если её нет
            state_dir = Path('data')
            state_dir.mkdir(exist_ok=True)
            
            state_file = state_dir / 'service_state.json'
            
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Состояние сохранено в {state_file}")
        except Exception as e:
            self.logger.error(f"❌ Ошибка сохранения состояния: {e}")
            self.logger.debug(f"Стек вызовов: {traceback.format_exc()}")


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
