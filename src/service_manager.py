#!/usr/bin/env python3
"""
Сервисный менеджер для автоматизации встреч
Обеспечивает работу в фоновом режиме с мониторингом и логированием
Поддерживает dual-account систему (личный и рабочий аккаунты)
"""

import os
import sys
import time
import signal
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
except ImportError as e:
    print(f"❌ Ошибка импорта dotenv: {e}")
    print("Установите: pip install python-dotenv")
    sys.exit(1)


class MeetingAutomationService:
    """Основной сервис автоматизации встреч с поддержкой dual-account."""
    
    def __init__(self, config_path: str = ".env"):
        """Инициализация сервиса."""
        self.config_path = config_path
        self.env = {}
        self.running = False
        self.thread = None
        self.logger = self._setup_logging()
        
        # Конфигурация сервиса
        self.config_manager = None
        self.check_interval = 300  # 5 минут между проверками
        self.media_check_interval = 1800  # 30 минут между проверками медиа
        self.media_processing_timeout = 1800  # 30 минут для медиа обработки
        self.last_media_check = None
        
        # Проверяем и настраиваем PATH для ffmpeg
        self._setup_ffmpeg_path()
        
        # Обработчики сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 Сервис автоматизации встреч инициализирован")
    
    def _setup_ffmpeg_path(self):
        """Настройка PATH для ffmpeg."""
        try:
            # Проверяем, доступен ли ffmpeg в текущем PATH
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.logger.info("✅ ffmpeg доступен в системе")
                return
        except Exception:
            pass
        
        # Пытаемся найти ffmpeg в стандартных местах
        ffmpeg_paths = [
            "/opt/homebrew/bin/ffmpeg",  # macOS Homebrew
            "/usr/local/bin/ffmpeg",     # macOS/Linux
            "/opt/homebrew/bin/ffmpeg",  # Apple Silicon Homebrew
        ]
        
        for path in ffmpeg_paths:
            if os.path.exists(path):
                # Добавляем путь в PATH
                current_path = os.environ.get('PATH', '')
                if path not in current_path:
                    os.environ['PATH'] = f"{path}:{current_path}"
                    self.logger.info(f"✅ Добавлен путь к ffmpeg: {path}")
                return
        
        self.logger.warning("⚠️ ffmpeg не найден в системе. Медиа обработка может не работать.")
    
    def _kill_hanging_ffmpeg_processes(self):
        """Останавливает зависшие FFmpeg процессы."""
        try:
            # Ищем процессы ffmpeg
            result = subprocess.run(['pgrep', '-f', 'ffmpeg'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                if pids and pids[0]:  # Проверяем, что есть процессы
                    self.logger.warning(f"⚠️ Найдены зависшие FFmpeg процессы: {pids}")
                    
                    for pid in pids:
                        if pid.strip():
                            try:
                                # Пытаемся остановить процесс
                                subprocess.run(['kill', '-TERM', pid.strip()], 
                                             capture_output=True, text=True, timeout=5)
                                self.logger.info(f"🔄 Отправлен сигнал TERM процессу FFmpeg PID: {pid}")
                            except Exception as e:
                                self.logger.error(f"❌ Не удалось остановить FFmpeg PID {pid}: {e}")
                    
                    # Ждем немного и проверяем, остались ли процессы
                    time.sleep(2)
                    result = subprocess.run(['pgrep', '-f', 'ffmpeg'], 
                                          capture_output=True, text=True, timeout=10)
                    
                    if result.returncode == 0:
                        remaining_pids = result.stdout.strip().split('\n')
                        if remaining_pids and remaining_pids[0]:
                            self.logger.warning(f"⚠️ Остались зависшие процессы: {remaining_pids}")
                            # Принудительно убиваем оставшиеся процессы
                            for pid in remaining_pids:
                                if pid.strip():
                                    try:
                                        subprocess.run(['kill', '-KILL', pid.strip()], 
                                                     capture_output=True, text=True, timeout=5)
                                        self.logger.info(f"💀 Принудительно остановлен FFmpeg PID: {pid}")
                                    except Exception as e:
                                        self.logger.error(f"❌ Не удалось принудительно остановить FFmpeg PID {pid}: {e}")
                else:
                    self.logger.info("✅ Зависших FFmpeg процессов не найдено")
            else:
                self.logger.info("✅ Зависших FFmpeg процессов не найдено")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка при проверке зависших FFmpeg процессов: {e}")
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования."""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем логгер
        logger = logging.getLogger("meeting_automation_service")
        logger.setLevel(logging.INFO)
        
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
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения."""
        self.logger.info(f"📡 Получен сигнал {signum}")
        self.stop()
    
    def load_environment(self) -> bool:
        """Загрузка переменных окружения."""
        try:
            # Загружаем основной .env файл
            if os.path.exists(self.config_path):
                load_dotenv(self.config_path)
                self.logger.info(f"✅ Загружен основной конфиг: {self.config_path}")
                
                # Инициализируем ConfigManager
                from src.config_manager import ConfigManager
                self.config_manager = ConfigManager(self.config_path)
                
                # Обновляем интервалы из конфигурации
                general_config = self.config_manager.get_general_config()
                self.check_interval = general_config.get('service_check_interval', 300)
                self.media_check_interval = general_config.get('service_media_interval', 1800)
                self.media_processing_timeout = general_config.get('media_processing_timeout', 1800)
                
                self.logger.info(f"⏰ Интервал проверки: {self.check_interval} секунд")
                self.logger.info(f"🎬 Интервал медиа: {self.media_check_interval} секунд")
                self.logger.info(f"⏰ Таймаут медиа: {self.media_processing_timeout} секунд")
                
                # Проверяем конфигурацию
                if self.config_manager.validate_config():
                    self.logger.info("✅ Конфигурация валидна")
                else:
                    self.logger.warning("⚠️ Конфигурация содержит ошибки")
                
                return True
            else:
                self.logger.error(f"❌ Файл конфигурации не найден: {self.config_path}")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки окружения: {e}")
            return False
    
    def run_personal_automation(self) -> Dict[str, Any]:
        """Запуск автоматизации для личного аккаунта."""
        try:
            self.logger.info("👤 Запуск автоматизации для личного аккаунта...")
            
            # Запускаем скрипт личного аккаунта
            result = subprocess.run([
                sys.executable, "meeting_automation_personal.py", "prepare"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("✅ Личный аккаунт: обработка завершена успешно")
                return {"status": "success", "output": result.stdout}
            else:
                self.logger.error(f"❌ Личный аккаунт: ошибка выполнения: {result.stderr}")
                return {"status": "error", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            error_msg = "⏰ Личный аккаунт: превышено время выполнения"
            self.logger.error(error_msg)
            return {"status": "timeout", "error": error_msg}
        except Exception as e:
            error_msg = f"❌ Личный аккаунт: неожиданная ошибка: {e}"
            self.logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def run_work_automation(self) -> Dict[str, Any]:
        """Запуск автоматизации для рабочего аккаунта."""
        try:
            self.logger.info("🏢 Запуск автоматизации для рабочего аккаунта...")
            
            # Запускаем скрипт рабочего аккаунта
            result = subprocess.run([
                sys.executable, "meeting_automation_work.py", "prepare"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                self.logger.info("✅ Рабочий аккаунт: обработка завершена успешно")
                return {"status": "success", "output": result.stdout}
            else:
                self.logger.error(f"❌ Рабочий аккаунт: ошибка выполнения: {result.stderr}")
                return {"status": "error", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            error_msg = "⏰ Рабочий аккаунт: превышено время выполнения"
            self.logger.error(error_msg)
            return {"status": "timeout", "error": error_msg}
        except Exception as e:
            error_msg = f"❌ Рабочий аккаунт: неожиданная ошибка: {e}"
            self.logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    def process_media_files(self) -> Dict[str, int]:
        """Обработка медиа файлов."""
        try:
            self.logger.info("🎬 Проверка медиа файлов...")
            
            # Используем таймаут из конфигурации
            media_timeout = self.media_processing_timeout
            self.logger.info(f"⏰ Таймаут медиа обработки: {media_timeout} секунд")
            
            # Проверяем, нужно ли обрабатывать медиа
            current_time = time.time()
            if hasattr(self, 'last_media_check') and self.last_media_check is not None and current_time - self.last_media_check < self.media_check_interval:
                self.logger.info("⏰ Медиа обработка еще не требуется")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0}
            
            total_processed = 0
            total_synced = 0
            total_errors = 0
            
                        # Запускаем медиа обработку для рабочего аккаунта
            self.logger.info("🎬 Запуск медиа обработки для рабочего аккаунта...")
            
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root', 'не указано')
                self.logger.info(f"📁 Обрабатываемые папки: {work_folder}")
                
                self.logger.info("🎥 Ищем видео файлы для обработки...")

                # Устанавливаем правильный PATH для FFmpeg
                env = os.environ.copy()
                env['PATH'] = f"/opt/homebrew/bin:{env.get('PATH', '')}"

                work_result = subprocess.run([
                    sys.executable, "meeting_automation_universal.py", "media", "--account", "work", "--quality", "medium"
                ], capture_output=True, text=True, timeout=media_timeout, env=env)
            else:
                self.logger.info("📁 Рабочий аккаунт отключен")
                work_result = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )
            
            if work_result.returncode == 0:
                self.logger.info("✅ Медиа обработка рабочего аккаунта завершена успешно")
                # Парсим результат для получения статистики
                if "📄 Файлов синхронизировано:" in work_result.stdout:
                    import re
                    synced_match = re.search(r"📄 Файлов синхронизировано: (\d+)", work_result.stdout)
                    processed_match = re.search(r"📁 Папок обработано: (\d+)", work_result.stdout)
                    
                    work_synced = int(synced_match.group(1)) if synced_match else 0
                    work_processed = int(processed_match.group(1)) if processed_match else 0
                    
                    total_synced += work_synced
                    total_processed += work_processed
                else:
                    self.logger.warning("⚠️ Не удалось получить статистику медиа обработки рабочего аккаунта")
            else:
                self.logger.error(f"❌ Ошибка медиа обработки рабочего аккаунта: {work_result.stderr}")
                total_errors += 1
            
                        # Запускаем медиа обработку для личного аккаунта
            self.logger.info("🎬 Запуск медиа обработки для личного аккаунта...")
            
            if self.config_manager and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root', 'не указано')
                self.logger.info(f"📁 Обрабатываемые папки: {personal_folder}")
                
                self.logger.info("🎥 Ищем видео файлы для обработки...")

                # Устанавливаем правильный PATH для FFmpeg
                env = os.environ.copy()
                env['PATH'] = f"/opt/homebrew/bin:{env.get('PATH', '')}"

                personal_result = subprocess.run([
                    sys.executable, "meeting_automation_universal.py", "media", "--account", "personal", "--quality", "medium"
                ], capture_output=True, text=True, timeout=media_timeout, env=env)
            else:
                self.logger.info("📁 Личный аккаунт отключен")
                personal_result = subprocess.CompletedProcess(
                    args=[], returncode=0, stdout="", stderr=""
                )
            
            if personal_result.returncode == 0:
                self.logger.info("✅ Медиа обработка личного аккаунта завершена успешно")
                self.logger.info(f"📤 Вывод команды: {personal_result.stdout[:500]}...")
                
                # Парсим результат для получения статистики
                if "📄 Файлов синхронизировано:" in personal_result.stdout:
                    import re
                    synced_match = re.search(r"📄 Файлов синхронизировано: (\d+)", personal_result.stdout)
                    processed_match = re.search(r"📁 Папок обработано: (\d+)", personal_result.stdout)
                    
                    personal_synced = int(synced_match.group(1)) if synced_match else 0
                    personal_processed = int(processed_match.group(1)) if processed_match else 0
                    
                    total_synced += personal_synced
                    total_processed += personal_processed
                    
                    self.logger.info(f"📊 Статистика личного аккаунта: синхронизировано={personal_synced}, обработано={personal_processed}")
                else:
                    self.logger.warning("⚠️ Не удалось получить статистику медиа обработки личного аккаунта")
                    self.logger.info(f"🔍 Поиск статистики в выводе: {personal_result.stdout}")
            else:
                self.logger.error(f"❌ Ошибка медиа обработки личного аккаунта: {personal_result.stderr}")
                self.logger.error(f"📤 Полный вывод команды: {personal_result.stdout}")
                self.logger.error(f"📤 Код возврата: {personal_result.returncode}")
                total_errors += 1
            
            # Обновляем время последней проверки медиа
            self.last_media_check = current_time
            
            return {"processed": total_processed, "synced": total_synced, "cleanup": 0, "errors": total_errors}
                
        except subprocess.TimeoutExpired:
            self.logger.error("⏰ Медиа обработка превысила время выполнения")
            self.logger.warning("⚠️ Проверяем и останавливаем зависшие FFmpeg процессы...")
            
            # Останавливаем зависшие FFmpeg процессы
            self._kill_hanging_ffmpeg_processes()
            
            # Обновляем время последней проверки медиа даже при ошибке
            self.last_media_check = current_time
            return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 1}
        except Exception as e:
            self.logger.error(f"❌ Ошибка медиа обработки: {e}")
            # Обновляем время последней проверки медиа даже при ошибке
            self.last_media_check = current_time
            return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 1}
    
    def send_telegram_notification(self, calendar_stats: Dict[str, Any], media_stats: Dict[str, Any]):
        """Отправка уведомлений в Telegram (заглушка для совместимости)."""
        # В новой системе уведомления отправляются из основных скриптов
        self.logger.info("📱 Уведомления отправляются из основных скриптов")
    
    def run_service_cycle(self):
        """Основной цикл работы сервиса."""
        try:
            self.logger.info("🔄 Запуск цикла обработки...")
            
            personal_stats = {"status": "skipped", "output": ""}
            work_stats = {"status": "skipped", "output": ""}
            
            # Запускаем автоматизацию для личного аккаунта
            if self.config_manager and self.config_manager.is_personal_enabled():
                self.logger.info("👤 Обрабатываю личный аккаунт...")
                personal_stats = self.run_personal_automation()
            else:
                self.logger.info("⏭️ Личный аккаунт пропущен (отключен в конфигурации)")
            
            # Запускаем автоматизацию для рабочего аккаунта
            if self.config_manager and self.config_manager.is_work_enabled():
                self.logger.info("🏢 Обрабатываю рабочий аккаунт...")
                work_stats = self.run_work_automation()
            else:
                self.logger.info("⏭️ Рабочий аккаунт пропущен (отключен в конфигурации)")
            
            # Обрабатываем медиа файлы (только если прошло достаточно времени)
            media_stats = self.process_media_files()
            
            # Логируем результаты
            self.logger.info(f"📊 Результаты цикла:")
            self.logger.info(f"   👤 Личный аккаунт: {personal_stats['status']}")
            self.logger.info(f"   🏢 Рабочий аккаунт: {work_stats['status']}")
            self.logger.info(f"   🎬 Медиа: {media_stats}")
            
            self.logger.info("✅ Цикл обработки завершен успешно")
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка в цикле сервиса: {e}")
    
    def service_worker(self):
        """Рабочий поток сервиса."""
        self.logger.info("👷 Рабочий поток сервиса запущен")
        
        while self.running:
            try:
                self.run_service_cycle()
                
                # Ждем до следующей проверки
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка в рабочем потоке: {e}")
                time.sleep(60)  # Ждем минуту при ошибке
    
    def start(self):
        """Запуск сервиса."""
        if self.running:
            self.logger.warning("⚠️ Сервис уже запущен")
            return
        
        # Загружаем окружение
        if not self.load_environment():
            self.logger.error("❌ Не удалось загрузить окружение")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.service_worker, daemon=True)
        self.thread.start()
        
        self.logger.info("🚀 Сервис запущен и работает в фоне")
        self.logger.info(f"⏰ Интервал проверки: {self.check_interval} секунд")
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
    
    args = parser.parse_args()
    
    # Создаем и запускаем сервис
    service = MeetingAutomationService(args.config)
    service.check_interval = args.interval
    service.media_check_interval = args.media_interval
    
    try:
        service.start()
    except Exception as e:
        print(f"❌ Критическая ошибка запуска сервиса: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
