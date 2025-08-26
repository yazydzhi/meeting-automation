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
    
    def _format_detailed_report(self, calendar_stats: Dict[str, Any], media_stats: Dict[str, Any]) -> str:
        """Формирование детального отчета для Telegram."""
        try:
            from datetime import datetime
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            report = f"""🤖 *ДЕТАЛЬНЫЙ ОТЧЕТ ОБ ОБРАБОТКЕ*

⏰ Время: {current_time}

🔄 *ОБРАБОТАННЫЕ ФАЙЛЫ:*

🎬 *МЕДИА ОБРАБОТКА:*
"""
            
            # Добавляем детали медиа обработки
            if media_stats.get("processed", 0) > 0:
                report += f"   • Обработано: {media_stats.get('processed', 0)} файлов\n"
                report += f"   • Найдено: {media_stats.get('synced', 0)} видео\n"
                
                # Добавляем детали по папкам
                if "results" in media_stats:
                    for result in media_stats["results"]:
                        if result.get("processed_files"):
                            report += f"\n📁 *{os.path.basename(result['folder'])}:*\n"
                            for file_info in result["processed_files"]:
                                if file_info.get("status") == "success":
                                    report += f"   ✅ {file_info['file']} → {os.path.basename(file_info['output'])}\n"
                                else:
                                    report += f"   ❌ {file_info['file']}: {file_info.get('error', 'ошибка')}\n"
            else:
                report += "   • Новых видео для обработки не найдено\n"
            
            report += f"\n🎤 *ТРАНСКРИПЦИЯ:*\n"
            
            # Добавляем детали транскрипции
            transcription_stats = getattr(self, 'last_transcription_stats', {})
            if transcription_stats.get("processed", 0) > 0:
                report += f"   • Обработано: {transcription_stats.get('processed', 0)} файлов\n"
                
                # Добавляем детали по файлам
                if "details" in transcription_stats:
                    for detail in transcription_stats["details"]:
                        report += f"\n📁 *{os.path.basename(detail['folder'])}:*\n"
                        for file_info in detail.get("files", []):
                            if file_info.get("status") == "success":
                                report += f"   ✅ {file_info['file']} → транскрипция создана\n"
                            elif file_info.get("status") == "already_exists":
                                report += f"   📄 {file_info['file']} → уже существует\n"
                            else:
                                report += f"   ❌ {file_info['file']}: {file_info.get('error', 'ошибка')}\n"
            else:
                report += "   • Новых аудио для транскрипции не найдено\n"
            
            report += f"\n📝 *NOTION СИНХРОНИЗАЦИЯ:*\n"
            
            # Добавляем детали Notion
            notion_stats = getattr(self, 'last_notion_stats', {})
            if notion_stats.get("synced", 0) > 0:
                report += f"   • Синхронизировано: {notion_stats.get('synced', 0)} записей\n"
                if "details" in notion_stats:
                    for detail in notion_stats["details"]:
                        report += f"   📋 {detail}\n"
            else:
                report += "   • Новых записей для синхронизации не найдено\n"
            
            report += f"\n👥 *СТАТУС АККАУНТОВ:*\n"
            report += f"   • Личный: ✅ {calendar_stats.get('personal', {}).get('status', 'unknown')}\n"
            report += f"   • Рабочий: ✅ {calendar_stats.get('work', {}).get('status', 'unknown')}\n"
            
            report += f"\n📊 *ОБЩАЯ СТАТИСТИКА:*\n"
            report += f"   • Медиа: {media_stats.get('processed', 0)} обработано\n"
            report += f"   • Транскрипция: {transcription_stats.get('processed', 0)} обработано\n"
            report += f"   • Notion: {notion_stats.get('synced', 0)} синхронизировано\n"
            
            report += f"\n🔄 *Следующая проверка:* через 5 минут\n"
            report += f"📱 *Уведомления:* автоматически\n"
            report += f"🤖 *Система:* meeting_automation"
            
            return report
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка формирования детального отчета: {e}")
            return f"❌ Ошибка формирования отчета: {str(e)}"
    
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
                    # Логируем детальную конфигурацию
                    self._log_configuration()
                else:
                    self.logger.warning("⚠️ Конфигурация содержит ошибки")
                
                return True
            else:
                self.logger.error(f"❌ Файл конфигурации не найден: {self.config_path}")
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
    
    def process_media_files(self) -> Dict[str, Any]:
        """Обработка медиа файлов."""
        try:
            current_time = time.time()
            
            # Проверяем, нужно ли запускать медиа обработку
            if hasattr(self, 'last_media_check') and (current_time - self.last_media_check) < self.media_check_interval:
                self.logger.info("⏰ Медиа обработка еще не требуется")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0}
            
            self.logger.info("🎬 Проверка медиа файлов...")
            media_timeout = self.config_manager.get_media_config().get('processing_timeout', 1800)
            self.logger.info(f"⏰ Таймаут медиа обработки: {media_timeout} секунд")
            
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
                # При локальной обработке статистика не нужна
                # Просто считаем успешное выполнение
                total_processed += 1
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
                # При локальной обработке статистика не нужна
                # Просто считаем успешное выполнение
                total_processed += 1
            else:
                self.logger.error(f"❌ Ошибка медиа обработки личного аккаунта: {personal_result.stderr}")
                total_errors += 1
            
            # Обновляем время последней проверки медиа
            self.last_media_check = current_time
            
            # Сохраняем статистику для детальных отчетов
            media_stats = {"processed": total_processed, "synced": total_synced, "cleanup": 0, "errors": total_errors}
            
            # Парсим результаты для детализации
            try:
                if work_result.returncode == 0 and work_result.stdout:
                    import json
                    # Ищем JSON в выводе
                    lines = work_result.stdout.split('\n')
                    for line in lines:
                        if line.strip().startswith('{') and line.strip().endswith('}'):
                            try:
                                data = json.loads(line.strip())
                                if 'results' in data:
                                    media_stats['results'] = data['results']
                                    break
                            except json.JSONDecodeError:
                                continue
                
                if personal_result.returncode == 0 and personal_result.stdout:
                    import json
                    # Ищем JSON в выводе
                    lines = personal_result.stdout.split('\n')
                    for line in lines:
                        if line.strip().startswith('{') and line.strip().endswith('}'):
                            try:
                                data = json.loads(line.strip())
                                if 'results' in data:
                                    if 'results' not in media_stats:
                                        media_stats['results'] = []
                                    media_stats['results'].extend(data['results'])
                                    break
                            except json.JSONDecodeError:
                                continue
                                
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось распарсить детали медиа обработки: {e}")
            
            return media_stats
                
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
        """Отправка уведомлений в Telegram с детализацией."""
        try:
            if not self.config_manager:
                self.logger.warning("⚠️ ConfigManager не инициализирован, уведомления не отправляются")
                return
            
            telegram_config = self.config_manager.get_telegram_config()
            if not telegram_config.get('bot_token') or not telegram_config.get('chat_id'):
                self.logger.warning("⚠️ Telegram не настроен, уведомления не отправляются")
                return
            
            # Формируем детальный отчет
            report = self._format_detailed_report(calendar_stats, media_stats)
            
            # Отправляем в Telegram
            self.logger.info("📱 Отправляю детальный отчет в Telegram...")
            
            # Используем универсальный скрипт для отправки
            try:
                notification_result = subprocess.run([
                    sys.executable, "meeting_automation_universal.py", "notify", 
                    "--message", report, "--type", "detailed"
                ], capture_output=True, text=True, timeout=60)
                
                if notification_result.returncode == 0:
                    self.logger.info("✅ Детальный отчет в Telegram отправлен")
                else:
                    self.logger.error(f"❌ Ошибка отправки в Telegram: {notification_result.stderr}")
                    
            except Exception as e:
                self.logger.error(f"❌ Ошибка отправки уведомления: {e}")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка формирования уведомления: {e}")
    
    def process_audio_transcription(self) -> Dict[str, Any]:
        """Обработка транскрипции аудио файлов."""
        try:
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
            
            # Сохраняем статистику для детальных отчетов
            self.last_notion_stats = notion_stats
            
            return notion_stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка синхронизации с Notion: {e}")
            error_stats = {"status": "error", "synced": 0, "errors": 1, "details": [str(e)]}
            self.last_notion_stats = error_stats
            return error_stats
    
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
    
    def run_service_cycle(self):
        """Основной цикл работы сервиса."""
        try:
            start_time = time.time()
            self.logger.info("🔄 Запуск цикла обработки...")
            self.logger.info(f"⏰ Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Загружаем предыдущее состояние
            self.previous_cycle_state = self._load_previous_state()
            
            personal_stats = {"status": "skipped", "output": ""}
            work_stats = {"status": "skipped", "output": ""}
            
            # Запускаем автоматизацию для личного аккаунта
            if self.config_manager and self.config_manager.is_personal_enabled():
                self.logger.info("👤 Обрабатываю личный аккаунт...")
                personal_start = time.time()
                personal_stats = self.run_personal_automation()
                personal_duration = time.time() - personal_start
                self.logger.info(f"⏱️ Время обработки личного аккаунта: {personal_duration:.2f} секунд")
            else:
                self.logger.info("⏭️ Личный аккаунт пропущен (отключен в конфигурации)")
            
            # Запускаем автоматизацию для рабочего аккаунта
            if self.config_manager and self.config_manager.is_work_enabled():
                self.logger.info("🏢 Обрабатываю рабочий аккаунт...")
                work_start = time.time()
                work_stats = self.run_work_automation()
                work_duration = time.time() - work_start
                self.logger.info(f"⏱️ Время обработки рабочего аккаунта: {work_duration:.2f} секунд")
            else:
                self.logger.info("⏭️ Рабочий аккаунт пропущен (отключен в конфигурации)")
            
            # Обрабатываем медиа файлы (только если прошло достаточно времени)
            self.logger.info("🎬 Запуск обработки медиа файлов...")
            media_start = time.time()
            media_stats = self.process_media_files()
            media_duration = time.time() - media_start
            self.logger.info(f"⏱️ Время обработки медиа: {media_duration:.2f} секунд")
            self.logger.info(f"📊 Результат обработки медиа: {media_stats}")
            
            # 🎤 ТРАНСКРИПЦИЯ АУДИО (каждый цикл)
            self.logger.info("🎤 Запуск транскрипции аудио...")
            self.logger.info("🔍 Проверка наличия аудио файлов для транскрипции...")
            transcription_start = time.time()
            transcription_stats = self.process_audio_transcription()
            transcription_duration = time.time() - transcription_start
            self.logger.info(f"⏱️ Время транскрипции: {transcription_duration:.2f} секунд")
            self.logger.info(f"📊 Результат транскрипции: обработано {transcription_stats.get('processed', 0)}, ошибок {transcription_stats.get('errors', 0)}")
            
            # 📝 СИНХРОНИЗАЦИЯ С NOTION (каждый цикл)
            self.logger.info("📝 Запуск синхронизации с Notion...")
            notion_start = time.time()
            notion_stats = self.sync_with_notion()
            notion_duration = time.time() - notion_start
            self.logger.info(f"⏱️ Время синхронизации с Notion: {notion_duration:.2f} секунд")
            self.logger.info(f"📊 Результат синхронизации с Notion: {notion_stats}")
            
            # Создаем текущее состояние цикла
            self.current_cycle_state = self._create_cycle_state(
                personal_stats, work_stats, media_stats, transcription_stats, notion_stats
            )
            
            # 📱 ОТПРАВКА УВЕДОМЛЕНИЙ В TELEGRAM (только при изменениях)
            self.logger.info("📱 Проверка необходимости отправки уведомлений в Telegram...")
            telegram_start = time.time()
            telegram_stats = self.send_telegram_notifications(
                self.current_cycle_state, self.previous_cycle_state
            )
            telegram_duration = time.time() - telegram_start
            self.logger.info(f"⏱️ Время отправки уведомлений: {telegram_duration:.2f} секунд")
            
            #  СОЗДАНИЕ ФАЙЛОВ СТАТУСА (каждый цикл)
            self.logger.info("📁 Создание файлов статуса...")
            status_start = time.time()
            self.create_status_files()
            status_duration = time.time() - status_start
            self.logger.info(f"⏱️ Время создания файлов статуса: {status_duration:.2f} секунд")
            
            # Сохраняем текущее состояние для следующего цикла
            self._save_current_state(self.current_cycle_state)
            
            # Логируем результаты
            total_duration = time.time() - start_time
            self.logger.info(f"📊 РЕЗУЛЬТАТЫ ЦИКЛА:")
            self.logger.info(f"   👤 Личный аккаунт: {personal_stats['status']}")
            self.logger.info(f"   🏢 Рабочий аккаунт: {work_stats['status']}")
            self.logger.info(f"   🎬 Медиа: обработано {media_stats.get('processed', 0)}, найдено {media_stats.get('synced', 0)}")
            self.logger.info(f"   🎤 Транскрипция: обработано {transcription_stats.get('processed', 0)}, ошибок {transcription_stats.get('errors', 0)}")
            self.logger.info(f"   📝 Notion: синхронизировано {notion_stats.get('synced', 0)}, ошибок {notion_stats.get('errors', 0)}")
            self.logger.info(f"   📱 Telegram: {telegram_stats.get('status', 'unknown')}")
            self.logger.info(f"⏱️ ОБЩЕЕ ВРЕМЯ ВЫПОЛНЕНИЯ ЦИКЛА: {total_duration:.2f} секунд")
            
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
