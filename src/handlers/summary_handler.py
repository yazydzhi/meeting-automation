#!/usr/bin/env python3
"""
Обработчик для создания саммари и анализа транскрипций.
"""

import os
import logging
from typing import Dict, Any, List
from .base_handler import BaseHandler
from .process_handler import ProcessHandler


class SummaryHandler(ProcessHandler):
    """Обработчик для создания саммари и анализа транскрипций."""
    
    def __init__(self, config_manager, transcription_handler=None, logger=None):
        super().__init__(config_manager, logger)
        self.transcription_handler = transcription_handler
        try:
            from prompt_manager import PromptManager
            self.prompt_manager = PromptManager(config_manager)
        except ImportError:
            self.prompt_manager = None
            self.logger.warning("⚠️ PromptManager не найден, используется базовая функциональность")
    
    def process(self, account_type: str = 'both') -> Dict[str, Any]:
        """
        Обработка саммари для указанного типа аккаунта.
        
        Args:
            account_type: Тип аккаунта ('personal', 'work', 'both')
            
        Returns:
            Результат обработки
        """
        try:
            self.logger.info("📋 Запуск обработки саммари...")
            
            results = []
            total_processed = 0
            total_errors = 0
            
            # Обрабатываем личный аккаунт
            if account_type in ['personal', 'both'] and self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_summaries(personal_folder, "personal")
                    results.append(personal_result)
                    total_processed += personal_result.get("processed", 0)
                    total_errors += personal_result.get("errors", 0)
                else:
                    self.logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
            
            # Обрабатываем рабочий аккаунт
            if account_type in ['work', 'both'] and self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_summaries(work_folder, "work")
                    results.append(work_result)
                    total_processed += work_result.get("processed", 0)
                    total_errors += work_result.get("errors", 0)
                else:
                    self.logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
            
            self.logger.info(f"✅ Обработка саммари завершена: {total_processed} обработано, {total_errors} ошибок")
            return {
                "status": "success",
                "message": "Summary processing completed",
                "results": results,
                "total_processed": total_processed,
                "total_errors": total_errors
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки саммари: {e}")
            return {"status": "error", "message": str(e)}
    
    def _process_folder_summaries(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Обрабатывает саммари для конкретной папки.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
        Returns:
            Результат обработки
        """
        try:
            result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
            
            # Ищем файлы транскрипций
            transcript_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('_transcript.txt'):
                        transcript_files.append(os.path.join(root, file))
            
            if not transcript_files:
                self.logger.info(f"📁 Файлы транскрипций не найдены в: {folder_path}")
                return result
            
            self.logger.info(f"📄 Найдено {len(transcript_files)} файлов транскрипций")
            
            # Обрабатываем каждый файл транскрипции
            for transcript_file in transcript_files:
                try:
                    if self._should_process_transcript_file(transcript_file):
                        if self._process_transcript_file(transcript_file):
                            result["processed"] += 1
                            result["files"].append({
                                "file": os.path.basename(transcript_file),
                                "status": "success"
                            })
                        else:
                            result["errors"] += 1
                            result["files"].append({
                                "file": os.path.basename(transcript_file),
                                "status": "error"
                            })
                    else:
                        result["files"].append({
                            "file": os.path.basename(transcript_file),
                            "status": "already_processed"
                        })
                        
                except Exception as e:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(transcript_file),
                        "status": "error",
                        "error": str(e)
                    })
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}
    
    def _should_process_transcript_file(self, file_path: str) -> bool:
        """
        Проверяет, нужно ли обрабатывать файл транскрипции.
        
        Args:
            file_path: Путь к файлу транскрипции
            
        Returns:
            True если файл нужно обрабатывать, False иначе
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Генерируем пути к файлам саммари и анализа
            base_path = os.path.splitext(file_path)[0]
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # TASK-2: Всегда обрабатываем все файлы транскрипций
            # для создания комплексных саммари, особенно когда есть несколько видео
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки необходимости обработки файла {file_path}: {e}")
            return False
    
    def _process_transcript_file(self, file_path: str) -> bool:
        """
        Обрабатывает файл транскрипции для создания саммари и анализа.
        
        Args:
            file_path: Путь к файлу транскрипции
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            self.logger.info(f"📋 Обрабатываю транскрипцию: {os.path.basename(file_path)}")
            
            # Генерируем пути к файлам
            base_path = os.path.splitext(file_path)[0]
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # Создаем базовое саммари
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"# Саммари транскрипции: {os.path.basename(file_path)}\n\n")
                f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                f.write(f"Статус: Базовое саммари\n\n")
                f.write("## Содержание:\n")
                f.write("Базовое саммари транскрипции\n")
            
            # Создаем файл анализа
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write('{\n')
                f.write('  "file": "' + os.path.basename(file_path) + '",\n')
                f.write('  "created": "' + self._get_current_timestamp() + '",\n')
                f.write('  "status": "generated",\n')
                f.write('  "analysis": "Базовый анализ транскрипции"\n')
                f.write('}\n')
            
            self.logger.info(f"✅ Созданы саммари и анализ: {summary_file}, {analysis_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки транскрипции {file_path}: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """
        Получает текущий timestamp.
        
        Returns:
            Строка с текущим временем
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def count_transcript_files(self, folder_path: str) -> int:
        """
        Подсчитывает количество файлов транскрипций для анализа.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Количество файлов
        """
        try:
            count = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('_transcript.txt'):
                        transcript_path = os.path.join(root, file)
                        # Проверяем, нужно ли обрабатывать
                        if self._should_process_transcript_file(transcript_path):
                            count += 1
            return count
        except Exception as e:
            self.logger.error(f"❌ Ошибка подсчета файлов транскрипций: {e}")
            return 0
    
    def get_openai_config(self) -> Dict[str, Any]:
        """
        Получает конфигурацию OpenAI для генерации саммари.
        
        Returns:
            Конфигурация OpenAI или пустой словарь
        """
        try:
            if hasattr(self.config_manager, 'get_openai_config'):
                return self.config_manager.get_openai_config()
            else:
                self.logger.warning("⚠️ ConfigManager не поддерживает get_openai_config")
                return {}
        except Exception as e:
            self.logger.error(f"❌ Ошибка получения конфигурации OpenAI: {e}")
            return {}
    
    def validate_openai_config(self) -> bool:
        """
        Проверяет корректность конфигурации OpenAI.
        
        Returns:
            True если конфигурация корректна, False иначе
        """
        try:
            openai_config = self.get_openai_config()
            api_key = openai_config.get('api_key')
            
            if not api_key:
                self.logger.error("❌ Не настроен API ключ OpenAI")
                return False
            
            self.logger.info("✅ Конфигурация OpenAI корректна")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка валидации конфигурации OpenAI: {e}")
            return False
