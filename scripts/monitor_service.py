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
    # Пытаемся импортировать из разных возможных мест
    try:
        from meeting_automation_personal_only import load_env_or_fail
    except ImportError:
        try:
            from src.config_manager import ConfigManager
            def load_env_or_fail():
                config = ConfigManager()
                return config.config
        except ImportError:
            print("❌ Не удалось импортировать модули проекта")
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
        
        # Загружаем окружение
        try:
            self.env = load_env_or_fail()
        except Exception as e:
            print(f"❌ Ошибка загрузки окружения: {e}")
            self.env = {}
    
    def check_service_process(self) -> dict:
        """Проверка процессов сервиса."""
        service_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
            try:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'service_manager.py' in cmdline:
                    service_processes.append({
                        'pid': proc.info['pid'],
                        'cpu_percent': proc.info['cpu_percent'],
                        'memory_mb': proc.info['memory_info'].rss / 1024 / 1024,
                        'cmdline': cmdline
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
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
        
        for log_file in log_files:
            if log_file.name.startswith("service_"):
                latest_log = log_file
                break
        
        if latest_log and latest_log.exists():
            try:
                # Читаем последние строки
                with open(latest_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Анализируем логи
                error_count = sum(1 for line in lines if 'ERROR' in line or '❌' in line)
                warning_count = sum(1 for line in lines if 'WARNING' in line or '⚠️' in line)
                info_count = sum(1 for line in lines if 'INFO' in line or '✅' in line)
                
                # Последняя активность
                last_activity = None
                for line in reversed(lines):
                    if 'INFO' in line or 'ERROR' in line or 'WARNING' in line:
                        try:
                            timestamp_str = line.split(' - ')[0]
                            last_activity = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                            break
                        except:
                            continue
                
                log_stats = {
                    'latest_file': latest_log.name,
                    'total_lines': len(lines),
                    'errors': error_count,
                    'warnings': warning_count,
                    'info': info_count,
                    'last_activity': last_activity,
                    'file_size_mb': latest_log.stat().st_size / 1024 / 1024
                }
                
            except Exception as e:
                log_stats = {'error': str(e)}
        else:
            log_stats = {'error': 'Логи не найдены'}
        
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
        token = self.env.get("TELEGRAM_BOT_TOKEN")
        chat_id = self.env.get("TELEGRAM_CHAT_ID")
        
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
            from meeting_automation_personal_only import get_google_services
            
            cal_svc, drive_svc = get_google_services(self.env)
            
            return {
                'calendar_available': cal_svc is not None,
                'drive_available': drive_svc is not None,
                'status': 'available'
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
                report += f"  • PID {proc['pid']}: CPU {proc['cpu_percent']:.1f}%, RAM {proc['memory_mb']:.1f}MB\n"
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
        if google_info['status'] == 'available':
            report += f"📅 Календарь: {'✅' if google_info['calendar_available'] else '❌'}\n"
            report += f"💾 Drive: {'✅' if google_info['drive_available'] else '❌'}\n"
        else:
            report += f"❌ Ошибка: {google_info['error']}\n"
        
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


def main():
    """Точка входа."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Мониторинг сервиса автоматизации встреч")
    parser.add_argument("--save", action="store_true", help="Сохранить отчет в файл")
    parser.add_argument("--continuous", action="store_true", help="Непрерывный мониторинг")
    parser.add_argument("--interval", type=int, default=60, help="Интервал мониторинга в секундах")
    
    args = parser.parse_args()
    
    monitor = ServiceMonitor()
    
    if args.continuous:
        print(f"🔄 Непрерывный мониторинг каждые {args.interval} секунд (Ctrl+C для остановки)")
        try:
            while True:
                monitor.run_monitoring(args.save)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n🛑 Мониторинг остановлен")
    else:
        monitor.run_monitoring(args.save)


if __name__ == "__main__":
    main()
