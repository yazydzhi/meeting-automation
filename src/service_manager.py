#!/usr/bin/env python3
"""
Сервисный менеджер для автоматизации встреч
Обеспечивает работу в фоновом режиме с мониторингом и логированием
"""

import os
import sys
import time
import signal
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from meeting_automation_personal_only import load_env_or_fail, get_google_services
    from src.media_processor import get_media_processor
    from src.drive_sync import get_drive_sync
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все зависимости установлены")
    sys.exit(1)


class MeetingAutomationService:
    """Основной сервис автоматизации встреч."""
    
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
            import subprocess
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
            "/usr/bin/ffmpeg",           # Linux
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
        
        # Файловый хендлер
        file_handler = logging.FileHandler(
            log_dir / f"service_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        
        # Консольный хендлер
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Добавляем хендлеры
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Обработчик сигналов для корректного завершения."""
        self.logger.info(f"📡 Получен сигнал {signum}, завершаю работу...")
        self.stop()
    
    def load_environment(self) -> bool:
        """Загрузка переменных окружения."""
        try:
            self.env = load_env_or_fail()
            self.logger.info("✅ Переменные окружения загружены")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка загрузки переменных окружения: {e}")
            return False
    
    def check_google_services(self) -> bool:
        """Проверка доступности Google сервисов."""
        try:
            cal_svc, drive_svc = get_google_services(self.env)
            self.env["drive_svc"] = drive_svc
            self.env["cal_svc"] = cal_svc  # Сохраняем cal_svc в env
            self.logger.info("✅ Google сервисы доступны")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка Google сервисов: {e}")
            return False
    
    def process_calendar_events(self) -> Dict[str, Any]:
        """Обработка событий календаря."""
        try:
            from meeting_automation_personal_only import (
                get_upcoming_events, should_process_event, process_event
            )
            
            # Получаем события на ближайшие 24 часа
            cal_id = self.env["PERSONAL_CALENDAR_ID"]
            cal_svc = self.env.get("cal_svc")
            
            if not cal_svc:
                self.logger.warning("⚠️ Google Calendar сервис недоступен")
                return {"processed": 0, "excluded": 0, "errors": 0, "details": []}
            
            events = get_upcoming_events(cal_id, cal_svc, 24, self.env["TIMEZONE"])
            
            # Фильтруем события
            filtered_events = []
            excluded_events = []
            
            for ev in events:
                title = ev.get("summary", "Без названия")
                if should_process_event(title):
                    filtered_events.append(ev)
                else:
                    excluded_events.append(title)
            
            # Обрабатываем события
            processed_count = 0
            processed_details = []
            for ev in filtered_events:
                try:
                    result = process_event(self.env, ev)
                    processed_count += 1
                    
                    # Собираем детали обработки
                    event_title = ev.get("summary", "Без названия")
                    event_time = ev.get("start", {}).get("dateTime", "Время не указано")
                    
                    detail = {
                        "title": event_title,
                        "time": event_time,
                        "result": result
                    }
                    processed_details.append(detail)
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки события {ev.get('summary')}: {e}")
            
            result = {
                "total": len(events),
                "processed": processed_count,
                "excluded": len(excluded_events),
                "errors": 0,
                "details": processed_details
            }
            
            if processed_count > 0:
                self.logger.info(f"✅ Обработано {processed_count} встреч")
            else:
                self.logger.info("📅 Новых встреч для обработки не найдено")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка обработки календаря: {e}")
            return {"processed": 0, "excluded": 0, "errors": 1, "details": []}
    
    def process_media_files(self) -> Dict[str, Any]:
        """Обработка медиа файлов."""
        try:
            if not get_media_processor or not get_drive_sync:
                self.logger.warning("⚠️ Модули медиа обработки недоступны")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0, "details": []}
            
            drive_svc = self.env.get("drive_svc")
            if not drive_svc:
                self.logger.warning("⚠️ Google Drive сервис недоступен")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0, "details": []}
            
            # Создаем синхронизатор и процессор
            drive_sync = get_drive_sync(drive_svc, self.env["MEDIA_SYNC_ROOT"])
            media_processor = get_media_processor(
                drive_svc, 
                self.env["MEDIA_OUTPUT_FORMAT"],
                video_compression=self.env.get("VIDEO_COMPRESSION", "true").lower() == "true",
                video_quality=self.env.get("VIDEO_QUALITY", "medium"),
                video_codec=self.env.get("VIDEO_CODEC", "h264")
            )
            
            # Получаем список папок для обработки
            parent_id = self.env.get("PERSONAL_DRIVE_PARENT_ID")
            if not parent_id:
                self.logger.warning("⚠️ PERSONAL_DRIVE_PARENT_ID не указан")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0, "details": []}
            
            # Ищем папки с событиями
            query = f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            folders_result = drive_svc.files().list(
                q=query,
                fields="files(id,name,createdTime)",
                orderBy="createdTime desc"
            ).execute()
            
            folders = folders_result.get("files", [])
            total_processed = 0
            total_synced = 0
            total_errors = 0
            media_details = []
            
            for folder in folders[:5]:  # Обрабатываем последние 5 папок
                folder_id = folder['id']
                folder_name = folder['name']
                
                try:
                    # Синхронизируем папку
                    sync_results = drive_sync.sync_folder(
                        folder_id, 
                        folder_name,
                        file_types=['video/*']
                    )
                    
                    total_synced += sync_results['files_synced']
                    
                    if sync_results['files_synced'] > 0:
                        # Получаем локальный путь
                        local_path = drive_sync.get_local_path(folder_name)
                        
                        # Обрабатываем медиа файлы
                        media_results = media_processor.process_folder(
                            folder_id, 
                            folder_name, 
                            local_path
                        )
                        
                        total_processed += media_results['files_processed']
                        total_errors += len(media_results['errors'])
                        
                        # Собираем детали медиа обработки
                        if media_results['files_processed'] > 0:
                            media_details.append({
                                "folder": folder_name,
                                "files_processed": media_results['files_processed'],
                                "files_found": media_results['files_found'],
                                "processing_time": media_results['processing_time']
                            })
                        
                        self.logger.info(f"🎬 Обработана папка {folder_name}: {media_results['files_processed']} файлов")
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки папки {folder_name}: {e}")
                    total_errors += 1
            
            # Очистка старых файлов
            cleanup_count = drive_sync.cleanup_old_files(self.env["MEDIA_CLEANUP_DAYS"])
            if cleanup_count > 0:
                self.logger.info(f"🧹 Очищено {cleanup_count} старых файлов")
            
            result = {
                "processed": total_processed,
                "synced": total_synced,
                "cleanup": cleanup_count,
                "errors": total_errors,
                "details": media_details
            }
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Критическая ошибка медиа обработки: {e}")
            return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 1, "details": []}
    
    def send_telegram_notification(self, calendar_stats: Dict[str, Any], media_stats: Dict[str, Any]):
        """Отправляет уведомление в Telegram."""
        try:
            from meeting_automation_personal_only import notify
            
            # Формируем детальный отчет
            report = "🤖 *ОТЧЕТ АВТОМАТИЗАЦИИ ВСТРЕЧ*\n"
            report += f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            # Статистика календаря
            if calendar_stats["processed"] > 0:
                report += f"📅 *КАЛЕНДАРЬ:*\n"
                report += f"• Обработано встреч: {calendar_stats['processed']}\n"
                if calendar_stats['excluded'] > 0:
                    report += f"• Исключено: {calendar_stats['excluded']}\n"
                report += "\n"
                
                # Детали по каждой встрече
                if calendar_stats.get('details'):
                    report += "*Обработанные встречи:*\n"
                    for detail in calendar_stats['details']:
                        title = detail.get('title', 'Без названия')
                        time_str = detail.get('time', 'Время не указано')
                        
                        # Форматируем время
                        try:
                            if 'T' in str(time_str):
                                # ISO формат времени
                                dt = datetime.fromisoformat(str(time_str).replace('Z', '+00:00'))
                                time_formatted = dt.strftime('%H:%M')
                            else:
                                time_formatted = str(time_str)
                        except:
                            time_formatted = str(time_str)
                        
                        report += f"  🕐 {time_formatted} | {title}\n"
                    report += "\n"
            
            # Статистика медиа
            if (media_stats["processed"] > 0 or media_stats["synced"] > 0 or 
                media_stats["cleanup"] > 0):
                report += f"🎬 *МЕДИА ОБРАБОТКА:*\n"
                if media_stats["processed"] > 0:
                    report += f"• Обработано видео: {media_stats['processed']}\n"
                if media_stats["synced"] > 0:
                    report += f"• Синхронизировано: {media_stats['synced']}\n"
                if media_stats["cleanup"] > 0:
                    report += f"• Очищено старых файлов: {media_stats['cleanup']}\n"
                report += "\n"
                
                # Детали по медиа обработке
                if media_stats.get('details'):
                    report += "*Обработанные папки:*\n"
                    for detail in media_stats['details']:
                        folder = detail.get('folder', 'Неизвестная папка')
                        processed = detail.get('files_processed', 0)
                        found = detail.get('files_found', 0)
                        time_sec = detail.get('processing_time', 0)
                        
                        report += f"  📁 {folder}\n"
                        report += f"    🎥 Найдено: {found} | ✅ Обработано: {processed}\n"
                        if time_sec > 0:
                            report += f"    ⏱️ Время: {time_sec:.1f} сек\n"
                    report += "\n"
            
            # Проверяем, есть ли реальные изменения
            has_changes = (
                calendar_stats["processed"] > 0 or 
                media_stats["processed"] > 0 or 
                media_stats["synced"] > 0 or 
                media_stats["cleanup"] > 0
            )
            
            if has_changes:
                notify(self.env, report)
                self.logger.info("📱 Детальное уведомление отправлено в Telegram")
            else:
                self.logger.info("📱 Уведомление не отправлено (изменений нет)")
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    def run_service_cycle(self):
        """Основной цикл работы сервиса."""
        self.logger.info("🔄 Запуск цикла обработки...")
        
        try:
            # Проверяем Google сервисы
            if not self.check_google_services():
                self.logger.error("❌ Google сервисы недоступны, пропускаю цикл")
                return
            
            # Обрабатываем события календаря
            calendar_stats = self.process_calendar_events()
            
            # Обрабатываем медиа файлы (реже)
            media_stats = {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0}
            if (self.last_media_check is None or 
                time.time() - self.last_media_check > self.media_check_interval):
                
                media_stats = self.process_media_files()
                self.last_media_check = time.time()
            
            # Отправляем уведомления
            self.send_telegram_notification(calendar_stats, media_stats)
            
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
