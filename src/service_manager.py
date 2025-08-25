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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
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
        
        # Состояние для отслеживания изменений
        self.previous_cycle_state = None
        self.current_cycle_state = None
        self.state_file_path = "data/service_state.json"
        
        # Создаем директорию для состояния
        self._ensure_state_directory()
        
        # Обработчики сигналов
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info("🚀 Сервис автоматизации встреч инициализирован")
    
    def _ensure_state_directory(self):
        """Создает директорию для сохранения состояния."""
        try:
            state_dir = Path(self.state_file_path).parent
            state_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось создать директорию состояния: {e}")
    
    def _load_previous_state(self) -> Optional[Dict[str, Any]]:
        """Загружает предыдущее состояние сервиса."""
        try:
            if os.path.exists(self.state_file_path):
                with open(self.state_file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось загрузить предыдущее состояние: {e}")
        return None
    
    def _save_current_state(self, state: Dict[str, Any]):
        """Сохраняет текущее состояние сервиса."""
        try:
            with open(self.state_file_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"⚠️ Не удалось сохранить текущее состояние: {e}")
    
    def _create_cycle_state(self, personal_stats: Dict[str, Any], work_stats: Dict[str, Any], 
                           media_stats: Dict[str, Any], transcription_stats: Dict[str, Any], 
                           notion_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Создает состояние текущего цикла для сравнения."""
        return {
            "timestamp": datetime.now().isoformat(),
            "personal_account": {
                "status": personal_stats.get("status", "unknown"),
                "has_changes": personal_stats.get("status") == "success" and personal_stats.get("output", "")
            },
            "work_account": {
                "status": work_stats.get("status", "unknown"),
                "has_changes": work_stats.get("status") == "success" and work_stats.get("output", "")
            },
            "media_processing": {
                "processed": media_stats.get("processed", 0),
                "synced": media_stats.get("synced", 0),
                "errors": media_stats.get("errors", 0),
                "has_changes": (media_stats.get("processed", 0) > 0 or 
                               media_stats.get("synced", 0) > 0 or 
                               media_stats.get("errors", 0) > 0)
            },
            "transcription": {
                "status": transcription_stats.get("status", "unknown"),
                "processed": transcription_stats.get("processed", 0),
                "errors": transcription_stats.get("errors", 0),
                "has_changes": (transcription_stats.get("processed", 0) > 0 or 
                               transcription_stats.get("errors", 0) > 0)
            },
            "notion_sync": {
                "status": notion_stats.get("status", "unknown"),
                "synced": notion_stats.get("synced", 0),
                "errors": notion_stats.get("errors", 0),
                "has_changes": (notion_stats.get("synced", 0) > 0 or 
                               notion_stats.get("errors", 0) > 0)
            }
        }
    
    def _has_significant_changes(self, current_state: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> bool:
        """Проверяет, есть ли значимые изменения для отправки уведомления."""
        if not previous_state:
            return True  # Первый запуск - отправляем уведомление
        
        # Проверяем изменения в медиа обработке
        if (current_state["media_processing"]["has_changes"] != previous_state["media_processing"]["has_changes"] or
            current_state["media_processing"]["processed"] != previous_state["media_processing"]["processed"] or
            current_state["media_processing"]["errors"] != previous_state["media_processing"]["errors"]):
            return True
        
        # Проверяем изменения в транскрипции
        if (current_state["transcription"]["has_changes"] != previous_state["transcription"]["has_changes"] or
            current_state["transcription"]["processed"] != previous_state["transcription"]["processed"] or
            current_state["transcription"]["errors"] != previous_state["transcription"]["errors"]):
            return True
        
        # Проверяем изменения в синхронизации с Notion
        if (current_state["notion_sync"]["has_changes"] != previous_state["notion_sync"]["has_changes"] or
            current_state["notion_sync"]["synced"] != previous_state["notion_sync"]["synced"] or
            current_state["notion_sync"]["errors"] != previous_state["notion_sync"]["errors"]):
            return True
        
        # Проверяем изменения в статусе аккаунтов
        if (current_state["personal_account"]["status"] != previous_state["personal_account"]["status"] or
            current_state["work_account"]["status"] != previous_state["work_account"]["status"]):
            return True
        
        return False
    
    def _format_detailed_report(self, current_state: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> str:
        """Формирует детальный отчет об изменениях для Telegram."""
        message = "🤖 <b>Отчет об изменениях в системе автоматизации встреч</b>\n\n"
        
        # Добавляем информацию о времени
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message += f"⏰ <b>Время:</b> {current_time}\n\n"
        
        # Анализируем изменения
        changes_detected = []
        
        # Медиа обработка
        if current_state["media_processing"]["has_changes"]:
            media_info = f"🎬 <b>Медиа обработка:</b>\n"
            media_info += f"   • Обработано: {current_state['media_processing']['processed']}\n"
            media_info += f"   • Синхронизировано: {current_state['media_processing']['synced']}\n"
            if current_state["media_processing"]["errors"] > 0:
                media_info += f"   • ❌ Ошибок: {current_state['media_processing']['errors']}\n"
            changes_detected.append(media_info)
        
        # Транскрипция
        if current_state["transcription"]["has_changes"]:
            trans_info = f"🎤 <b>Транскрипция:</b>\n"
            trans_info += f"   • Обработано: {current_state['transcription']['processed']}\n"
            if current_state["transcription"]["errors"] > 0:
                trans_info += f"   • ❌ Ошибок: {current_state['transcription']['errors']}\n"
            changes_detected.append(trans_info)
        
        # Синхронизация с Notion
        if current_state["notion_sync"]["has_changes"]:
            notion_info = f"📝 <b>Синхронизация с Notion:</b>\n"
            notion_info += f"   • Синхронизировано: {current_state['notion_sync']['synced']}\n"
            if current_state["notion_sync"]["errors"] > 0:
                notion_info += f"   • ❌ Ошибок: {current_state['notion_sync']['errors']}\n"
            changes_detected.append(notion_info)
        
        # Статус аккаунтов
        personal_status = "✅" if current_state["personal_account"]["status"] == "success" else "❌"
        work_status = "✅" if current_state["work_account"]["status"] == "success" else "❌"
        
        account_info = f"👥 <b>Статус аккаунтов:</b>\n"
        account_info += f"   • Личный: {personal_status} {current_state['personal_account']['status']}\n"
        account_info += f"   • Рабочий: {work_status} {current_state['work_account']['status']}\n"
        changes_detected.append(account_info)
        
        if changes_detected:
            message += "🔄 <b>Обнаружены изменения:</b>\n\n"
            message += "\n".join(changes_detected)
        else:
            message += "✅ <b>Изменений не обнаружено</b>\n"
        
        # Добавляем общую статистику
        message += f"\n📊 <b>Общая статистика цикла:</b>\n"
        message += f"   • Медиа: {current_state['media_processing']['processed']} обработано\n"
        message += f"   • Транскрипция: {current_state['transcription']['processed']} обработано\n"
        message += f"   • Notion: {current_state['notion_sync']['synced']} синхронизировано\n"
        
        total_errors = (current_state["media_processing"]["errors"] + 
                       current_state["transcription"]["errors"] + 
                       current_state["notion_sync"]["errors"])
        
        if total_errors > 0:
            message += f"   • ❌ Всего ошибок: {total_errors}\n"
        
        return message
    
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
            
            # Запускаем универсальный скрипт для личного аккаунта
            result = subprocess.run([
                sys.executable, "meeting_automation_universal.py", "calendar", "--account", "personal"
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
            
            # Запускаем универсальный скрипт для рабочего аккаунта
            result = subprocess.run([
                sys.executable, "meeting_automation_universal.py", "calendar", "--account", "work"
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
    
    def process_audio_transcription(self) -> Dict[str, Any]:
        """Обработка транскрипции аудио файлов."""
        try:
            self.logger.info("🎤 Начинаю обработку транскрипции аудио...")
            
            transcription_stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
            
            # Обрабатываем личный аккаунт
            if self.config_manager and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_transcription(personal_folder, "personal")
                    transcription_stats["details"].append(personal_result)
                    transcription_stats["processed"] += personal_result.get("processed", 0)
                    transcription_stats["errors"] += personal_result.get("errors", 0)
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_transcription(work_folder, "work")
                    transcription_stats["details"].append(work_result)
                    transcription_stats["processed"] += work_result.get("processed", 0)
                    transcription_stats["errors"] += work_result.get("errors", 0)
            
            self.logger.info(f"✅ Транскрипция завершена: обработано {transcription_stats['processed']}, ошибок {transcription_stats['errors']}")
            return transcription_stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка транскрипции: {e}")
            return {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
    
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
    
    def sync_with_notion(self) -> Dict[str, Any]:
        """Синхронизация с Notion."""
        try:
            self.logger.info("📝 Начинаю синхронизацию с Notion...")
            
            notion_stats = {"status": "success", "synced": 0, "errors": 0, "details": []}
            
            # Получаем настройки Notion
            if not self.config_manager:
                return {"status": "error", "synced": 0, "errors": 1, "details": ["ConfigManager не инициализирован"]}
            
            notion_config = self.config_manager.get_notion_config()
            if not notion_config.get('token'):
                return {"status": "error", "synced": 0, "errors": 1, "details": ["Токен Notion не настроен"]}
            
            # Запускаем синхронизацию через универсальный скрипт
            try:
                sync_result = subprocess.run([
                    sys.executable, "meeting_automation_universal.py", "notion", "--account", "both"
                ], capture_output=True, text=True, timeout=300)  # 5 минут на синхронизацию
                
                if sync_result.returncode == 0:
                    notion_stats["synced"] = 1
                    notion_stats["details"].append("Синхронизация с Notion завершена успешно")
                    self.logger.info("✅ Синхронизация с Notion завершена")
                else:
                    notion_stats["errors"] = 1
                    notion_stats["details"].append(f"Ошибка синхронизации: {sync_result.stderr}")
                    self.logger.error(f"❌ Ошибка синхронизации с Notion: {sync_result.stderr}")
                    
            except subprocess.TimeoutExpired:
                notion_stats["errors"] = 1
                notion_stats["details"].append("Таймаут синхронизации с Notion")
                self.logger.error("⏰ Таймаут синхронизации с Notion")
            except Exception as e:
                notion_stats["errors"] = 1
                notion_stats["details"].append(f"Ошибка синхронизации: {str(e)}")
                self.logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
            
            return notion_stats
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка синхронизации с Notion: {e}")
            return {"status": "error", "synced": 0, "errors": 1, "details": [str(e)]}
    
    def send_telegram_notifications(self, current_state: Dict[str, Any], previous_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Отправка умных уведомлений в Telegram только при наличии изменений."""
        try:
            # Проверяем, есть ли значимые изменения
            if not self._has_significant_changes(current_state, previous_state):
                self.logger.info("📱 Изменений не обнаружено - уведомление не отправляется")
                return {"status": "skipped", "sent": 0, "errors": 0, "details": ["Изменений не обнаружено"]}
            
            self.logger.info("📱 Обнаружены изменения - отправляю уведомление в Telegram...")
            
            telegram_stats = {"status": "success", "sent": 0, "errors": 0, "details": []}
            
            # Получаем настройки Telegram
            if not self.config_manager:
                return {"status": "error", "sent": 0, "errors": 1, "details": ["ConfigManager не инициализирован"]}
            
            telegram_config = self.config_manager.get_telegram_config()
            if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
                return {"status": "error", "sent": 0, "errors": 1, "details": ["Настройки Telegram неполные"]}
            
            # Формируем детальный отчет об изменениях
            try:
                detailed_message = self._format_detailed_report(current_state, previous_state)
                
                # Отправляем через Python requests
                try:
                    import requests
                    
                    message_data = {
                        "chat_id": telegram_config['chat_id'],
                        "text": detailed_message,
                        "parse_mode": "HTML"
                    }
                    
                    response = requests.post(
                        f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage",
                        json=message_data,
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        telegram_stats["sent"] = 1
                        telegram_stats["details"].append("Детальный отчет об изменениях отправлен успешно")
                        self.logger.info("✅ Детальный отчет в Telegram отправлен")
                    else:
                        telegram_stats["errors"] = 1
                        telegram_stats["errors"] = 1
                        telegram_stats["details"].append(f"Ошибка отправки: HTTP {response.status_code}")
                        self.logger.error(f"❌ Ошибка отправки в Telegram: HTTP {response.status_code}")
                        
                except ImportError:
                    # Fallback к curl если requests не доступен
                    import subprocess
                    import json
                    
                    message_data = {
                        "chat_id": telegram_config['chat_id'],
                        "text": detailed_message,
                        "parse_mode": "HTML"
                    }
                    
                    curl_result = subprocess.run([
                        "curl", "-s", "-X", "POST",
                        f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage",
                        "-H", "Content-Type: application/json",
                        "-d", json.dumps(message_data)
                    ], capture_output=True, text=True, timeout=30)
                    
                    if curl_result.returncode == 0:
                        telegram_stats["sent"] = 1
                        telegram_stats["details"].append("Детальный отчет об изменениях отправлен успешно")
                        self.logger.info("✅ Детальный отчет в Telegram отправлен")
                    else:
                        telegram_stats["errors"] = 1
                        telegram_stats["details"].append(f"Ошибка отправки: {curl_result.stderr}")
                        self.logger.error(f"❌ Ошибка отправки в Telegram: {curl_result.stderr}")
                    
            except subprocess.TimeoutExpired:
                telegram_stats["errors"] = 1
                telegram_stats["details"].append("Таймаут отправки в Telegram")
                self.logger.error("⏰ Таймаут отправки в Telegram")
            except Exception as e:
                telegram_stats["errors"] = 1
                telegram_stats["details"].append(f"Ошибка отправки: {str(e)}")
                self.logger.error(f"❌ Ошибка отправки в Telegram: {e}")
            
            return telegram_stats
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка отправки в Telegram: {e}")
            return {"status": "error", "sent": 0, "errors": 1, "details": [str(e)]}
    
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
        """Создание видимых файлов статуса в папках аккаунтов."""
        try:
            self.logger.info("📁 Создаю файлы статуса в папках аккаунтов...")
            
            # Обрабатываем личный аккаунт
            if self.config_manager and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self._create_folder_status_file(personal_folder, "personal")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self._create_folder_status_file(work_folder, "work")
            
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
    
    def run_service_cycle(self):
        """Основной цикл работы сервиса."""
        try:
            self.logger.info("🔄 Запуск цикла обработки...")
            
            # Загружаем предыдущее состояние
            self.previous_cycle_state = self._load_previous_state()
            
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
            
            # 🎤 ТРАНСКРИПЦИЯ АУДИО (каждый цикл)
            self.logger.info("🎤 Запуск транскрипции аудио...")
            transcription_stats = self.process_audio_transcription()
            
            # 📝 СИНХРОНИЗАЦИЯ С NOTION (каждый цикл)
            self.logger.info("📝 Запуск синхронизации с Notion...")
            notion_stats = self.sync_with_notion()
            
            # Создаем текущее состояние цикла
            self.current_cycle_state = self._create_cycle_state(
                personal_stats, work_stats, media_stats, transcription_stats, notion_stats
            )
            
            # 📱 ОТПРАВКА УВЕДОМЛЕНИЙ В TELEGRAM (только при изменениях)
            self.logger.info("📱 Проверка необходимости отправки уведомлений в Telegram...")
            telegram_stats = self.send_telegram_notifications(
                self.current_cycle_state, self.previous_cycle_state
            )
            
            # 📁 СОЗДАНИЕ ФАЙЛОВ СТАТУСА (каждый цикл)
            self.logger.info("📁 Создание файлов статуса...")
            self.create_status_files()
            
            # Сохраняем текущее состояние для следующего цикла
            self._save_current_state(self.current_cycle_state)
            
            # Логируем результаты
            self.logger.info(f"📊 Результаты цикла:")
            self.logger.info(f"   👤 Личный аккаунт: {personal_stats['status']}")
            self.logger.info(f"   🏢 Рабочий аккаунт: {work_stats['status']}")
            self.logger.info(f"   🎬 Медиа: {media_stats}")
            self.logger.info(f"   🎤 Транскрипция: {transcription_stats}")
            self.logger.info(f"   📝 Notion: {notion_stats}")
            self.logger.info(f"   📱 Telegram: {telegram_stats}")
            
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
