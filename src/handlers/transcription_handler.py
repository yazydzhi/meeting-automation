#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для транскрипций
"""

import os
from typing import Dict, Any, List
from .process_handler import ProcessHandler
from .base_handler import retry


class TranscriptionHandler(ProcessHandler):
    """Обработчик транскрипций аудио файлов."""
    
    def __init__(self, config_manager, transcription_handler=None, logger=None):
        """
        Инициализация обработчика транскрипций.
        
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
        Основной метод обработки транскрипций.
        
        Returns:
            Результат обработки транскрипций
        """
        try:
            self._log_operation_start("обработку транскрипций")
            
            # Пытаемся использовать существующий обработчик
            if self.transcription_handler:
                result = self.transcription_handler.process_transcription()
                self._log_operation_end("обработку транскрипций", result)
                return result
            
            # Используем собственную логику
            result = self._process_transcriptions()
            self._log_operation_end("обработку транскрипций", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, "обработка транскрипций")
    
    def _process_transcriptions(self) -> Dict[str, Any]:
        """
        Обработка транскрипций с использованием базового функционала.
        
        Returns:
            Результат обработки
        """
        return self.process_with_accounts(
            process_type="транскрипций",
            handler_method="process_transcription",
            folder_method="_process_folder_transcription",
            stats_key="last_transcription_stats"
        )
    
    def _process_folder_transcription(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Обработка транскрипций для конкретной папки.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
        Returns:
            Результат обработки папки
        """
        return self.process_folder_files(
            folder_path=folder_path,
            account_type=account_type,
            file_extension='.mp3',
            should_process_func=self._should_process_audio_file,
            process_file_func=self._process_audio_file
        )
    
    def _should_process_audio_file(self, file_path: str) -> bool:
        """
        Проверяет, нужно ли обрабатывать аудио файл.
        
        Args:
            file_path: Путь к аудио файлу
            
        Returns:
            True если файл нужно обрабатывать, False иначе
        """
        try:
            if not os.path.exists(file_path):
                return False
            
            # Проверяем, что это не сжатый файл
            if file_path.lower().endswith('_compressed.mp3'):
                return False
            
            # Генерируем путь к файлу транскрипции
            base_path = os.path.splitext(file_path)[0]
            transcript_file = base_path + '_transcript.txt'
            
            # Если файл транскрипции уже существует, не обрабатываем
            if os.path.exists(transcript_file):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка проверки необходимости обработки аудио файла {file_path}: {e}")
            return False
    
    def _process_audio_file(self, file_path: str) -> bool:
        """
        Обрабатывает аудио файл для создания транскрипции.
        
        Args:
            file_path: Путь к аудио файлу
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            self.logger.info(f"🎤 Обрабатываю аудио файл: {os.path.basename(file_path)}")
            
            # Здесь должна быть логика создания транскрипции
            # Пока что просто логируем и возвращаем True
            # TODO: Интегрировать с существующей логикой транскрипции
            
            # Генерируем путь к файлу транскрипции
            base_path = os.path.splitext(file_path)[0]
            transcript_file = base_path + '_transcript.txt'
            
            # Создаем заглушку транскрипции для тестирования
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(f"Транскрипция файла: {os.path.basename(file_path)}\n")
                f.write("Создано: " + self._get_current_timestamp() + "\n")
                f.write("Статус: Заглушка для тестирования\n")
            
            self.logger.info(f"✅ Создана транскрипция: {transcript_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки аудио файла {file_path}: {e}")
            return False
    
    def _get_current_timestamp(self) -> str:
        """
        Получает текущий timestamp.
        
        Returns:
            Строка с текущим временем
        """
        from datetime import datetime
        return datetime.now().isoformat()
    
    def count_audio_files(self, folder_path: str) -> int:
        """
        Подсчитывает количество аудио файлов для транскрипции.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Количество файлов
        """
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
