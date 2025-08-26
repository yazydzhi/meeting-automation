#!/usr/bin/env python3
"""
Менеджер логов для системы автоматизации встреч.
Обеспечивает ротацию, очистку и управление лог файлами.
"""

import os
import sys
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any
import argparse

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.config_manager import ConfigManager
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что вы запускаете скрипт из корневой директории проекта")
    sys.exit(1)


class LogManager:
    """Менеджер логов системы."""
    
    def __init__(self, config_path: str = ".env"):
        """Инициализация менеджера логов."""
        self.config_manager = ConfigManager(config_path)
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        
        # Настройки логирования из конфигурации
        self.log_level = self.config_manager.get_general_config().get('log_level', 'INFO')
        self.retention_days = int(os.getenv('LOG_RETENTION_DAYS', '30'))
        self.max_size_mb = int(os.getenv('LOG_MAX_SIZE_MB', '100'))
        self.backup_count = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        self.rotation_enabled = os.getenv('LOG_ROTATION_ENABLED', 'true').lower() == 'true'
        
        # Настройка логирования для самого менеджера
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка логирования для менеджера логов."""
        logger = logging.getLogger("log_manager")
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        self.logger = logger
    
    def get_log_files(self) -> Dict[str, Dict[str, Any]]:
        """Получить информацию о всех лог файлах."""
        log_files = {}
        
        if not self.logs_dir.exists():
            return log_files
        
        for log_file in self.logs_dir.glob("*.log"):
            stat = log_file.stat()
            log_files[log_file.name] = {
                'path': log_file,
                'size_mb': stat.st_size / (1024 * 1024),
                'modified': datetime.fromtimestamp(stat.st_mtime),
                'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
            }
        
        return log_files
    
    def analyze_logs(self) -> Dict[str, Any]:
        """Анализ текущего состояния логов."""
        log_files = self.get_log_files()
        
        analysis = {
            'total_files': len(log_files),
            'total_size_mb': sum(info['size_mb'] for info in log_files.values()),
            'files': log_files,
            'duplicates': [],
            'old_files': [],
            'large_files': []
        }
        
        # Поиск дублирующих файлов
        file_types = {}
        for name, info in log_files.items():
            base_name = name.replace('.log', '').replace('_', '').lower()
            if base_name not in file_types:
                file_types[base_name] = []
            file_types[base_name].append(name)
        
        for base_name, files in file_types.items():
            if len(files) > 1:
                analysis['duplicates'].extend(files[1:])  # Оставляем первый файл
        
        # Поиск старых файлов
        for name, info in log_files.items():
            if info['age_days'] > self.retention_days:
                analysis['old_files'].append(name)
        
        # Поиск больших файлов
        for name, info in log_files.items():
            if info['size_mb'] > self.max_size_mb:
                analysis['large_files'].append(name)
        
        return analysis
    
    def rotate_logs(self):
        """Ротация лог файлов."""
        if not self.rotation_enabled:
            self.logger.info("⚠️ Ротация логов отключена")
            return
        
        log_files = self.get_log_files()
        
        for name, info in log_files.items():
            if info['size_mb'] > self.max_size_mb:
                self.logger.info(f"🔄 Ротация лога: {name} ({info['size_mb']:.1f} MB)")
                
                # Создаем резервную копию с временной меткой
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{name}.{timestamp}"
                backup_path = self.logs_dir / backup_name
                
                try:
                    # Переименовываем текущий файл
                    shutil.move(info['path'], backup_path)
                    
                    # Создаем новый пустой файл
                    info['path'].touch()
                    
                    self.logger.info(f"✅ Лог ротирован: {backup_name}")
                    
                    # Удаляем старые резервные копии
                    self._cleanup_old_backups(name)
                    
                except Exception as e:
                    self.logger.error(f"❌ Ошибка ротации {name}: {e}")
    
    def _cleanup_old_backups(self, base_name: str):
        """Очистка старых резервных копий."""
        pattern = f"{base_name}.*"
        backup_files = list(self.logs_dir.glob(pattern))
        
        # Сортируем по дате модификации
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Удаляем лишние файлы
        if len(backup_files) > self.backup_count:
            for old_file in backup_files[self.backup_count:]:
                try:
                    old_file.unlink()
                    self.logger.info(f"🗑️ Удалена старая резервная копия: {old_file.name}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка удаления {old_file.name}: {e}")
    
    def cleanup_old_logs(self):
        """Очистка старых лог файлов."""
        log_files = self.get_log_files()
        deleted_count = 0
        deleted_size = 0
        
        for name, info in log_files.items():
            if info['age_days'] > self.retention_days:
                try:
                    info['path'].unlink()
                    deleted_count += 1
                    deleted_size += info['size_mb']
                    self.logger.info(f"🗑️ Удален старый лог: {name} ({info['age_days']} дней)")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка удаления {name}: {e}")
        
        if deleted_count > 0:
            self.logger.info(f"✅ Очищено {deleted_count} файлов, освобождено {deleted_size:.1f} MB")
        else:
            self.logger.info("✅ Старые логи не найдены")
    
    def consolidate_logs(self):
        """Консолидация лог файлов в основные категории."""
        log_files = self.get_log_files()
        
        # Определяем основные категории логов
        main_categories = {
            'service': ['service.log', 'service_error.log'],
            'universal': ['meeting_automation_universal.log', 'universal_automation.log'],
            'audio': ['audio_processing.log', 'mp3_processing.log']
        }
        
        for category, files in main_categories.items():
            existing_files = [f for f in files if f in log_files]
            
            if len(existing_files) > 1:
                self.logger.info(f"🔄 Консолидация логов категории: {category}")
                
                # Оставляем основной файл, остальные удаляем
                main_file = existing_files[0]
                files_to_delete = existing_files[1:]
                
                for file_to_delete in files_to_delete:
                    try:
                        (self.logs_dir / file_to_delete).unlink()
                        self.logger.info(f"🗑️ Удален дублирующий лог: {file_to_delete}")
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка удаления {file_to_delete}: {e}")
    
    def print_analysis(self):
        """Вывод анализа логов в консоль."""
        analysis = self.analyze_logs()
        
        print("\n📊 АНАЛИЗ ЛОГ ФАЙЛОВ")
        print("=" * 50)
        print(f"📁 Всего файлов: {analysis['total_files']}")
        print(f"💾 Общий размер: {analysis['total_size_mb']:.1f} MB")
        print(f"🔄 Ротация: {'✅ Включена' if self.rotation_enabled else '❌ Отключена'}")
        print(f"⏰ Время хранения: {self.retention_days} дней")
        print(f"📏 Максимальный размер: {self.max_size_mb} MB")
        print(f"📦 Количество резервных копий: {self.backup_count}")
        
        if analysis['files']:
            print(f"\n📋 ДЕТАЛИ ФАЙЛОВ:")
            for name, info in analysis['files'].items():
                status_icons = []
                if name in analysis['duplicates']:
                    status_icons.append("🔄")
                if name in analysis['duplicates']:
                    status_icons.append("⏰")
                if name in analysis['large_files']:
                    status_icons.append("📏")
                
                status = " ".join(status_icons) if status_icons else "✅"
                print(f"   {status} {name}: {info['size_mb']:.1f} MB, {info['age_days']} дней")
        
        if analysis['duplicates']:
            print(f"\n�� ДУБЛИРУЮЩИЕ ФАЙЛЫ:")
            for duplicate in analysis['duplicates']:
                print(f"   - {duplicate}")
        
        if analysis['old_files']:
            print(f"\n⏰ СТАРЫЕ ФАЙЛЫ (> {self.retention_days} дней):")
            for old_file in analysis['old_files']:
                print(f"   - {old_file}")
        
        if analysis['large_files']:
            print(f"\n📏 БОЛЬШИЕ ФАЙЛЫ (> {self.max_size_mb} MB):")
            for large_file in analysis['large_files']:
                print(f"   - {large_file}")
    
    def optimize_logs(self):
        """Полная оптимизация системы логов."""
        self.logger.info("🚀 Начинаю оптимизацию системы логов...")
        
        # Анализ текущего состояния
        self.print_analysis()
        
        # Консолидация дублирующих файлов
        self.logger.info("\n🔄 Консолидация лог файлов...")
        self.consolidate_logs()
        
        # Ротация больших файлов
        self.logger.info("\n🔄 Ротация больших лог файлов...")
        self.rotate_logs()
        
        # Очистка старых файлов
        self.logger.info("\n🗑️ Очистка старых лог файлов...")
        self.cleanup_old_logs()
        
        # Финальный анализ
        self.logger.info("\n📊 Финальный анализ после оптимизации...")
        self.print_analysis()
        
        self.logger.info("✅ Оптимизация логов завершена")


def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(description="Менеджер логов системы автоматизации встреч")
    parser.add_argument("--config", default=".env", help="Путь к файлу конфигурации")
    parser.add_argument("--action", choices=["analyze", "rotate", "cleanup", "consolidate", "optimize"], 
                       default="analyze", help="Действие для выполнения")
    parser.add_argument("--retention-days", type=int, help="Количество дней хранения логов")
    parser.add_argument("--max-size-mb", type=int, help="Максимальный размер лог файла в MB")
    
    args = parser.parse_args()
    
    # Создаем менеджер логов
    log_manager = LogManager(args.config)
    
    # Применяем переопределенные параметры
    if args.retention_days:
        log_manager.retention_days = args.retention_days
    if args.retention_days:
        log_manager.max_size_mb = args.max_size_mb
    
    # Выполняем действие
    if args.action == "analyze":
        log_manager.print_analysis()
    elif args.action == "rotate":
        log_manager.rotate_logs()
    elif args.action == "cleanup":
        log_manager.cleanup_old_logs()
    elif args.action == "consolidate":
        log_manager.consolidate_logs()
    elif args.action == "optimize":
        log_manager.optimize_logs()


if __name__ == "__main__":
    main()
