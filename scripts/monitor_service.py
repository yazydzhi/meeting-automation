#!/usr/bin/env python3
"""
Мониторинг сервиса автоматизации встреч
Проверяет статус, логи и производительность
"""

import os
import sys
import time
import psutil
import requests
from datetime import datetime, timedelta
from pathlib import Path
import json

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    # Импортируем ConfigManager для загрузки конфигурации
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Не удалось импортировать ConfigManager: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Ошибка импорта: {e}")
    sys.exit(1)


class ServiceMonitor:
    """Мониторинг сервиса автоматизации встреч."""
    
    def __init__(self):
        """Инициализация монитора."""
        self.project_dir = Path(__file__).parent.parent
        self.logs_dir = self.project_dir / "logs"
        self.data_dir = self.project_dir / "data"
        
        # Создаем папку logs если её нет
        if not self.logs_dir.exists():
            self.logs_dir.mkdir(exist_ok=True)
            print(f"📁 Создана папка логов: {self.logs_dir}")
        
        # Создаем папку data если её нет
        if not self.data_dir.exists():
            self.data_dir.mkdir(exist_ok=True)
            print(f"📁 Создана папка данных: {self.data_dir}")
        
        # Загружаем окружение
        try:
            config_manager = ConfigManager()
            self.env = config_manager.config
        except Exception as e:
            print(f"❌ Ошибка загрузки окружения: {e}")
            self.env = {}
    
    def check_service_process(self) -> dict:
        """Проверка процессов сервиса."""
        service_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'service_manager.py' in cmdline:
                    # Получаем время создания процесса (запуска)
                    create_time = datetime.fromtimestamp(proc.info['create_time'])
                    uptime = datetime.now() - create_time
                    
                    service_processes.append({
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'start_time': create_time,
                        'uptime': uptime,
                        'cmdline': cmdline
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Сохраняем время запуска для использования в логах
        if service_processes:
            self._service_start_time = service_processes[0]['start_time']
        
        return {
            'running': len(service_processes) > 0,
            'processes': service_processes,
            'count': len(service_processes)
        }
    
    def check_logs(self) -> dict:
        """Проверка логов сервиса."""
        log_files = list(self.logs_dir.glob("*.log"))
        latest_log = None
        log_stats = {}
        
        # Показываем информацию о найденных логах
        if log_files:
            print(f"📁 Найдено логов в {self.logs_dir}: {len(log_files)}")
            for log_file in log_files:
                size_mb = log_file.stat().st_size / 1024 / 1024
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                print(f"   📄 {log_file.name} ({size_mb:.2f}MB, изменен {mtime.strftime('%H:%M:%S')})")
        else:
            print(f"⚠️ Логи не найдены в {self.logs_dir}")
        
        # Ищем основной лог сервиса
        for log_file in log_files:
            if log_file.name.startswith("meeting_automation_service"):
                latest_log = log_file
                break
        
        # Если не нашли основной лог, ищем любой лог
        if not latest_log and log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
        
        if latest_log and latest_log.exists():
            try:
                # Читаем последние строки
                with open(latest_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Получаем время запуска сервиса из текущего процесса
                service_start_time = None
                if hasattr(self, '_service_start_time'):
                    service_start_time = self._service_start_time
                else:
                    # Ищем в логах последний запуск сервиса
                    for line in reversed(lines):
                        if '🚀 Сервис запущен' in line or 'Сервис автоматизации встреч инициализирован' in line or '🚀 Инициализация менеджера сервиса' in line:
                            try:
                                timestamp_str = line.split(' - ')[0]
                                service_start_time = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                                break
                            except:
                                continue
                    
                    # Если не нашли, используем время создания файла
                    if not service_start_time:
                        service_start_time = datetime.fromtimestamp(latest_log.stat().st_ctime)
                    
                    # Сохраняем время запуска для использования в других функциях
                    self._service_start_time = service_start_time
                
                # Фильтруем логи только с момента запуска сервиса
                filtered_lines = []
                for line in lines:
                    try:
                        timestamp_str = line.split(' - ')[0]
                        line_time = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                        if line_time >= service_start_time:
                            filtered_lines.append(line)
                    except:
                        # Если не можем распарсить время, добавляем строку
                        filtered_lines.append(line)
                
                # Анализируем отфильтрованные логи
                error_count = sum(1 for line in filtered_lines if 'ERROR' in line or '❌' in line)
                warning_count = sum(1 for line in filtered_lines if 'WARNING' in line or '⚠️' in line)
                info_count = sum(1 for line in filtered_lines if 'INFO' in line or '✅' in line)
                
                # Последняя активность
                last_activity = None
                for line in reversed(filtered_lines):
                    if 'INFO' in line or 'ERROR' in line or 'WARNING' in line:
                        try:
                            timestamp_str = line.split(' - ')[0]
                            last_activity = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                            break
                        except:
                            continue
                
                # Собираем warning и error записи для отображения
                warning_lines = []
                error_lines = []
                
                for line in filtered_lines:
                    if 'WARNING' in line or '⚠️' in line:
                        warning_lines.append(line.strip())
                    elif 'ERROR' in line or '❌' in line:
                        error_lines.append(line.strip())
                
                log_stats = {
                    'latest_file': latest_log.name,
                    'total_lines': len(filtered_lines),
                    'errors': error_count,
                    'warnings': warning_count,
                    'info': info_count,
                    'last_activity': last_activity,
                    'file_size_mb': latest_log.stat().st_size / 1024 / 1024,
                    'service_start_time': service_start_time,
                    'warning_lines': warning_lines,
                    'error_lines': error_lines
                }
                
            except Exception as e:
                log_stats = {'error': str(e)}
        else:
            log_stats = {'error': f'Логи не найдены в {self.logs_dir}'}
        
        return log_stats
    
    def check_data_directory(self) -> dict:
        """Проверка директории данных."""
        synced_dir = self.data_dir / "synced"
        sync_status_file = synced_dir / ".sync_status.json"
        
        data_stats = {
            'synced_dir_exists': synced_dir.exists(),
            'sync_status_exists': sync_status_file.exists(),
            'total_size_mb': 0,
            'file_count': 0
        }
        
        if synced_dir.exists():
            try:
                total_size = 0
                file_count = 0
                
                for file_path in synced_dir.rglob("*"):
                    if file_path.is_file():
                        total_size += file_path.stat().st_size
                        file_count += 1
                
                data_stats['total_size_mb'] = total_size / 1024 / 1024
                data_stats['file_count'] = file_count
                
            except Exception as e:
                data_stats['error'] = str(e)
        
        return data_stats
    
    def check_telegram_connection(self) -> dict:
        """Проверка подключения к Telegram."""
        # Получаем токены из конфигурации
        token = self.env.get("telegram", {}).get("bot_token")
        chat_id = self.env.get("telegram", {}).get("chat_id")
        
        if not token or not chat_id:
            return {'available': False, 'error': 'Токены не настроены'}
        
        try:
            # Проверяем информацию о боте
            response = requests.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10
            )
            response.raise_for_status()
            
            bot_info = response.json()
            if bot_info.get('ok'):
                return {
                    'available': True,
                    'bot_name': bot_info['result']['first_name'],
                    'username': bot_info['result']['username']
                }
            else:
                return {'available': False, 'error': 'Ошибка API Telegram'}
                
        except Exception as e:
            return {'available': False, 'error': str(e)}
    
    def check_google_services(self) -> dict:
        """Проверка Google сервисов."""
        try:
            # Проверяем настройки Google сервисов из конфигурации
            if not self.env:
                return {
                    'calendar_available': False,
                    'drive_available': False,
                    'status': 'not_configured',
                    'error': 'Конфигурация не загружена'
                }
            
            # Проверяем наличие настроек для личного аккаунта
            personal_calendar = self.env.get('accounts', {}).get('personal', {}).get('calendar_provider')
            personal_drive = self.env.get('accounts', {}).get('personal', {}).get('drive_provider')
            
            # Проверяем наличие настроек для рабочего аккаунта
            work_calendar = self.env.get('accounts', {}).get('work', {}).get('calendar_provider')
            work_drive = self.env.get('accounts', {}).get('work', {}).get('drive_provider')
            
            calendar_available = personal_calendar or work_calendar
            drive_available = personal_drive or work_drive
            
            return {
                'calendar_available': bool(calendar_available),
                'drive_available': bool(drive_available),
                'status': 'configured',
                'personal_calendar': personal_calendar,
                'personal_drive': personal_drive,
                'work_calendar': work_calendar,
                'work_drive': work_drive
            }
            
        except Exception as e:
            return {
                'calendar_available': False,
                'drive_available': False,
                'status': 'error',
                'error': str(e)
            }
    
    def generate_report(self) -> str:
        """Генерация отчета о состоянии сервиса."""
        print("🔍 Проверка состояния сервиса...")
        
        # Собираем данные
        process_info = self.check_service_process()
        log_info = self.check_logs()
        data_info = self.check_data_directory()
        telegram_info = self.check_telegram_connection()
        google_info = self.check_google_services()
        
        # Формируем отчет
        report = "📊 *ОТЧЕТ О СОСТОЯНИИ СЕРВИСА*\n\n"
        
        # Статус процессов
        report += "🖥️ *ПРОЦЕССЫ:*\n"
        if process_info['running']:
            report += f"✅ Сервис запущен ({process_info['count']} процессов)\n"
            for proc in process_info['processes']:
                start_time_str = proc['start_time'].strftime("%H:%M:%S")
                uptime_hours = proc['uptime'].total_seconds() // 3600
                uptime_minutes = (proc['uptime'].total_seconds() % 3600) // 60
                uptime_str = f"{int(uptime_hours)}ч {int(uptime_minutes)}м"
                
                report += f"  • PID {proc['pid']}: запущен в {start_time_str} (работает {uptime_str})\n"
                report += f"    CPU {proc['cpu_percent']:.1f}%, RAM {proc['memory_mb']:.1f}MB\n"
        else:
            report += "❌ Сервис не запущен\n"
        report += "\n"
        
        # Логи
        report += "📋 *ЛОГИ:*\n"
        if 'error' not in log_info:
            report += f"📄 Файл: {log_info['latest_file']}\n"
            report += f"📊 Строк: {log_info['total_lines']}\n"
            report += f"❌ Ошибок: {log_info['errors']}\n"
            report += f"⚠️ Предупреждений: {log_info['warnings']}\n"
            report += f"✅ Инфо: {log_info['info']}\n"
            report += f"💾 Размер: {log_info['file_size_mb']:.2f}MB\n"
            
            if log_info['last_activity']:
                time_diff = datetime.now() - log_info['last_activity']
                if time_diff < timedelta(minutes=5):
                    report += f"🕐 Последняя активность: {time_diff.seconds // 60} мин назад\n"
                else:
                    report += f"🕐 Последняя активность: {time_diff.seconds // 3600} ч назад\n"
            
            # Добавляем информацию о времени запуска сервиса
            if 'service_start_time' in log_info and log_info['service_start_time']:
                service_uptime = datetime.now() - log_info['service_start_time']
                uptime_hours = service_uptime.total_seconds() // 3600
                uptime_minutes = (service_uptime.total_seconds() % 3600) // 60
                uptime_str = f"{int(uptime_hours)}ч {int(uptime_minutes)}м"
                report += f"🕐 Время запуска: {log_info['service_start_time'].strftime('%H:%M:%S')} (работает {uptime_str})\n"
        else:
            report += f"❌ Ошибка: {log_info['error']}\n"
        report += "\n"
        
        # Данные
        report += "💾 *ДАННЫЕ:*\n"
        if data_info['synced_dir_exists']:
            report += f"📁 Синхронизировано: {data_info['file_count']} файлов\n"
            report += f"💾 Общий размер: {data_info['total_size_mb']:.2f}MB\n"
        else:
            report += "❌ Директория данных не найдена\n"
        report += "\n"
        
        # Telegram
        report += "📱 *TELEGRAM:*\n"
        if telegram_info['available']:
            report += f"✅ Доступен: @{telegram_info['username']}\n"
        else:
            report += f"❌ Недоступен: {telegram_info['error']}\n"
        report += "\n"
        
        # Google сервисы
        report += "🔗 *GOOGLE СЕРВИСЫ:*\n"
        if google_info['status'] == 'configured':
            report += f"📅 Календарь: {'✅' if google_info['calendar_available'] else '❌'}\n"
            report += f"💾 Drive: {'✅' if google_info['drive_available'] else '❌'}\n"
            if google_info.get('personal_calendar'):
                report += f"   👤 Личный: {google_info['personal_calendar']}\n"
            if google_info.get('work_calendar'):
                report += f"   🏢 Рабочий: {google_info['work_calendar']}\n"
        elif google_info['status'] == 'not_configured':
            report += "❌ Не настроены\n"
        else:
            error_msg = google_info.get('error', 'Неизвестная ошибка')
            report += f"❌ Ошибка: {error_msg}\n"
        
        # Добавляем warning и error записи
        if 'warning_lines' in log_info and log_info['warning_lines']:
            report += "\n⚠️ *ПРЕДУПРЕЖДЕНИЯ:*\n"
            for warning in log_info['warning_lines'][-3:]:  # Показываем последние 3
                # Убираем timestamp для краткости
                if ' - ' in warning:
                    warning_content = warning.split(' - ', 1)[1]
                    report += f"   {warning_content}\n"
                else:
                    report += f"   {warning}\n"
        
        if 'error_lines' in log_info and log_info['error_lines']:
            report += "\n❌ *ОШИБКИ:*\n"
            for error in log_info['error_lines'][-3:]:  # Показываем последние 3
                # Убираем timestamp для краткости
                if ' - ' in error:
                    error_content = error.split(' - ', 1)[1]
                    report += f"   {error_content}\n"
                else:
                    report += f"   {error}\n"
        
        return report
    
    def save_report(self, report: str):
        """Сохранение отчета в файл."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.logs_dir / f"monitor_report_{timestamp}.txt"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 Отчет сохранен: {report_file}")
        except Exception as e:
            print(f"❌ Ошибка сохранения отчета: {e}")
    
    def run_monitoring(self, save_to_file: bool = False):
        """Запуск мониторинга."""
        print("🚀 Запуск мониторинга сервиса автоматизации встреч")
        print(f"📁 Директория проекта: {self.project_dir}")
        print("=" * 60)
        
        report = self.generate_report()
        
        # Выводим в консоль
        print(report)
        
        # Сохраняем в файл если нужно
        if save_to_file:
            self.save_report(report)
        
        print("=" * 60)
        print("✅ Мониторинг завершен")
    
    def run_continuous_monitoring(self, interval: int = 1, save_to_file: bool = False):
        """Запуск непрерывного мониторинга."""
        print("🔄 Запуск непрерывного мониторинга")
        print(f"⏱️ Интервал обновления: {interval} секунд")
        print("🛑 Нажмите Ctrl+C для остановки")
        print("=" * 60)
        
        try:
            while True:
                # Очищаем экран для лучшего отображения
                os.system('clear' if os.name == 'posix' else 'cls')
                
                # Показываем текущее время
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"🕐 {current_time}")
                print("=" * 60)
                
                # Генерируем и показываем отчет
                report = self.generate_report()
                print(report)
                
                # Показываем статус мониторинга
                print("=" * 60)
                print(f"🔄 Следующее обновление через {interval} секунд... (Ctrl+C для остановки)")
                
                # Ждем указанный интервал
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Получен сигнал остановки...")
            print("📊 Генерируем финальный отчет...")
            
            # Показываем финальный отчет
            final_report = self.generate_report()
            print("\n" + "=" * 60)
            print("📊 ФИНАЛЬНЫЙ ОТЧЕТ")
            print("=" * 60)
            print(final_report)
            
            # Сохраняем финальный отчет
            if save_to_file:
                self.save_report(final_report)
            
            print("\n✅ Мониторинг остановлен")
            print("👋 До свидания!")
        except Exception as e:
            print(f"\n❌ Ошибка в мониторинге: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
            self.run_continuous_monitoring(interval, save_to_file)


def main():
    """Точка входа."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Мониторинг сервиса автоматизации встреч")
    parser.add_argument("--save", action="store_true", help="Сохранить отчет в файл")
    parser.add_argument("--continuous", action="store_true", help="Непрерывный мониторинг")
    parser.add_argument("--interval", type=int, default=1, help="Интервал мониторинга в секундах (по умолчанию 1)")
    parser.add_argument("--once", action="store_true", help="Одноразовая проверка (по умолчанию)")
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor()
    
    if args.continuous:
        # Непрерывный мониторинг
        monitor.run_continuous_monitoring(args.interval, args.save)
    else:
        # Одноразовая проверка
        monitor.run_monitoring(args.save)


if __name__ == "__main__":
    main()
