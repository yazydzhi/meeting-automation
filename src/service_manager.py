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
        self.check_interval = 300  # 5 минут между проверками
        self.media_check_interval = 1800  # 30 минут между проверками медиа
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
    
    def _setup_logging(self) -> logging.Logger:
        """Настройка логирования."""
        # Создаем директорию для логов
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Настраиваем логгер
        logger = logging.getLogger("meeting_automation_service")
        logger.setLevel(logging.INFO)
        
        # Форматтер
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Хендлер для файла
        file_handler = logging.FileHandler(log_dir / "service.log")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Хендлер для консоли
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Добавляем хендлеры
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
            
            # Проверяем наличие конфигураций для dual-account
            personal_config = "env.personal"
            work_config = "env.work"
            
            if os.path.exists(personal_config):
                self.logger.info(f"✅ Найдена конфигурация личного аккаунта: {personal_config}")
            
            if os.path.exists(work_config):
                self.logger.info(f"✅ Найдена конфигурация рабочего аккаунта: {work_config}")
            
            return True
            
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
            work_result = subprocess.run([
                sys.executable, "meeting_automation_work.py", "media", "--quality", "medium"
            ], capture_output=True, text=True, timeout=600)
            
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
            self.logger.info("📁 Команда: meeting_automation_personal.py media --quality medium")
            personal_result = subprocess.run([
                sys.executable, "meeting_automation_personal.py", "media", "--quality", "medium"
            ], capture_output=True, text=True, timeout=600)
            
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
            
            # Запускаем автоматизацию для личного аккаунта
            personal_stats = self.run_personal_automation()
            
            # Запускаем автоматизацию для рабочего аккаунта
            work_stats = self.run_work_automation()
            
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
