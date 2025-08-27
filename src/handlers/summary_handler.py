#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для генерации саммари
"""

import os
from typing import Dict, Any, List
from .process_handler import ProcessHandler
from .base_handler import retry


class SummaryHandler(ProcessHandler):
    """Обработчик генерации саммари для транскрипций."""
    
    def __init__(self, config_manager, transcription_handler=None, logger=None):
        """
        Инициализация обработчика саммари.
        
        Args:
            config_manager: Менеджер конфигурации
            transcription_handler: Существующий обработчик транскрипций (если есть)
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.transcription_handler = transcription_handler
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Основной метод генерации саммари.
        
        Returns:
            Результат генерации саммари
        """
        try:
            self._log_operation_start("генерацию саммари")
            
            # Пытаемся использовать существующий обработчик
            if self.transcription_handler:
                result = self.transcription_handler.process_summaries()
                self._log_operation_end("генерацию саммари", result)
                return result
            
            # Используем собственную логику
            result = self._process_summaries()
            self._log_operation_end("генерацию саммари", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, "генерация саммари")
    
    def _process_summaries(self) -> Dict[str, Any]:
        """
        Генерация саммари с использованием базового функционала.
        
        Returns:
            Результат обработки
        """
        return self.process_with_accounts(
            process_type="саммари",
            handler_method="process_summaries",
            folder_method="_process_folder_summaries",
            stats_key="last_summary_stats"
        )
    
    def _process_folder_summaries(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Генерация саммари для транскрипций в конкретной папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
        Returns:
            Результат обработки папки
        """
        return self.process_folder_files(
            folder_path=folder_path,
            account_type=account_type,
            file_extension='_transcript.txt',
            should_process_func=self._should_process_transcript_file,
            process_file_func=self._process_transcript_file
        )
    
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
            
            # Проверяем, что это файл транскрипции
            if not file_path.lower().endswith('_transcript.txt'):
                return False
            
            # Генерируем пути к выходным файлам
            base_path = file_path.replace('_transcript.txt', '')
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # Если саммари или анализ уже существуют, не обрабатываем
            if os.path.exists(summary_file) or os.path.exists(analysis_file):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки необходимости обработки транскрипции {file_path}: {e}")
            return False
    
    def _process_transcript_file(self, file_path: str) -> bool:
        """
        Обрабатывает файл транскрипции для создания саммари.
        
        Args:
            file_path: Путь к файлу транскрипции
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            self.logger.info(f"📝 Обрабатываю транскрипцию: {os.path.basename(file_path)}")
            
            # Здесь должна быть логика генерации саммари
            # Пока что просто логируем и возвращаем True
            # TODO: Интегрировать с существующей логикой генерации саммари
            
            # Генерируем пути к выходным файлам
            base_path = file_path.replace('_transcript.txt', '')
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # Создаем заглушку саммари для тестирования
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(f"Саммари транскрипции: {os.path.basename(file_path)}\n")
                f.write("Создано: " + self._get_current_timestamp() + "\n")
                f.write("Статус: Заглушка для тестирования\n")
                f.write("Содержание: Краткое резюме встречи\n")
            
            # Создаем заглушку анализа для тестирования
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write('{\n')
                f.write('  "file": "' + os.path.basename(file_path) + '",\n')
                f.write('  "created": "' + self._get_current_timestamp() + '",\n')
                f.write('  "status": "Заглушка для тестирования",\n')
                f.write('  "analysis": "Анализ содержания встречи"\n')
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
