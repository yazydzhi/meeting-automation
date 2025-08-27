#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовый класс для обработки файлов в папках
"""

import os
from typing import Dict, Any, List, Callable, Optional
from .base_handler import BaseHandler


class ProcessHandler(BaseHandler):
    """Базовый класс для обработки файлов в папках."""
    
    def __init__(self, config_manager, logger=None):
        """
        Инициализация обработчика файлов.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер
        """
        super().__init__(config_manager, logger)
    
    def process_with_accounts(self, 
                            process_type: str,
                            handler_method: str,
                            folder_method: str,
                            stats_key: str) -> Dict[str, Any]:
        """
        Общий метод для обработки с аккаунтами.
        
        Args:
            process_type: Тип обработки (для логирования)
            handler_method: Метод обработчика для вызова
            folder_method: Метод обработки папки
            stats_key: Ключ для сохранения статистики
            
        Returns:
            Результат обработки
        """
        try:
            self._log_operation_start(f"генерацию {process_type}")
            
            stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
            has_files = False
            
            # Обрабатываем личный аккаунт
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Проверка {process_type} в папке личного аккаунта: {personal_folder}")
                    personal_result = getattr(self, folder_method)(personal_folder, "personal")
                    if personal_result["processed"] > 0:
                        has_files = True
                        stats["details"].append(personal_result)
                        stats["processed"] += personal_result.get("processed", 0)
                        stats["errors"] += personal_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке личного аккаунта нет {process_type} для обработки")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Проверка {process_type} в папке рабочего аккаунта: {work_folder}")
                    work_result = getattr(self, folder_method)(work_folder, "work")
                    if work_result["processed"] > 0:
                        has_files = True
                        stats["details"].append(work_result)
                        stats["processed"] += work_result.get("processed", 0)
                        stats["errors"] += work_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке рабочего аккаунта нет {process_type} для обработки")
            
            if not has_files:
                self.logger.info(f"📂 Нет {process_type} для обработки")
                stats["status"] = "no_files"
            
            self.logger.info(f"✅ Генерация {process_type} завершена: обработано {stats['processed']}, ошибок {stats['errors']}")
            
            # Сохраняем статистику для детальных отчетов
            setattr(self, stats_key, stats)
            
            return stats
            
        except Exception as e:
            return self._create_error_result(e, f"генерация {process_type}")
    
    def process_folder_files(self, 
                           folder_path: str, 
                           account_type: str, 
                           file_extension: str,
                           should_process_func: Callable[[str], bool],
                           process_file_func: Callable[[str], bool]) -> Dict[str, Any]:
        """
        Общий метод для обработки файлов в папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            file_extension: Расширение файлов для поиска
            should_process_func: Функция проверки необходимости обработки
            process_file_func: Функция обработки файла
            
        Returns:
            Результат обработки папки
        """
        try:
            result = {
                "account": account_type, 
                "folder": folder_path, 
                "processed": 0, 
                "errors": 0, 
                "files": []
            }
            
            # Ищем файлы для обработки
            files_to_process = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(file_extension):
                        file_path = os.path.join(root, file)
                        # Проверяем, нужно ли обрабатывать
                        if should_process_func(file_path):
                            files_to_process.append(file_path)
            
            if not files_to_process:
                self.logger.info(f"📁 В папке {folder_path} нет файлов для обработки")
                return result
            
            self.logger.info(f"📄 Найдено {len(files_to_process)} файлов для обработки")
            
            # Обрабатываем файлы
            for file_path in files_to_process:
                try:
                    if process_file_func(file_path):
                        result["processed"] += 1
                        result["files"].append(file_path)
                        self.logger.debug(f"✅ Обработан файл: {file_path}")
                    else:
                        result["errors"] += 1
                        self.logger.warning(f"⚠️ Не удалось обработать файл: {file_path}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки {file_path}: {e}")
                    result["errors"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            result["errors"] += 1
            return result
    
    def count_files_by_extension(self, folder_path: str, file_extension: str) -> int:
        """
        Подсчитывает количество файлов с указанным расширением.
        
        Args:
            folder_path: Путь к папке
            file_extension: Расширение файлов
            
        Returns:
            Количество файлов
        """
        try:
            count = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(file_extension):
                        count += 1
            return count
        except Exception as e:
            self.logger.error(f"❌ Ошибка подсчета файлов {file_extension} в {folder_path}: {e}")
            return 0
    
    def find_files_by_extension(self, folder_path: str, file_extension: str) -> List[str]:
        """
        Находит все файлы с указанным расширением.
        
        Args:
            folder_path: Путь к папке
            file_extension: Расширение файлов
            
        Returns:
            Список путей к файлам
        """
        try:
            files = []
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    if filename.lower().endswith(file_extension):
                        file_path = os.path.join(root, filename)
                        files.append(file_path)
            return files
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска файлов {file_extension} в {folder_path}: {e}")
            return []
    
    def should_process_file(self, file_path: str, output_file_path: str = None) -> bool:
        """
        Проверяет, нужно ли обрабатывать файл.
        
        Args:
            file_path: Путь к входному файлу
            output_file_path: Путь к выходному файлу (если не указан, генерируется)
            
        Returns:
            True если файл нужно обрабатывать, False иначе
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Если выходной файл не указан, генерируем путь
            if output_file_path is None:
                base_path = os.path.splitext(file_path)[0]
                # Определяем расширение выходного файла на основе типа обработки
                if file_path.lower().endswith('.mp3'):
                    output_file_path = base_path + '_transcript.txt'
                elif file_path.lower().endswith('_transcript.txt'):
                    output_file_path = base_path + '_summary.txt'
                else:
                    # Для других типов файлов не можем определить
                    return True
            
            # Проверяем, существует ли уже выходной файл
            if os.path.exists(output_file_path):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки необходимости обработки {file_path}: {e}")
            return False
