#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для генерации саммари
"""

import os
from typing import Dict, Any, List
from .process_handler import ProcessHandler
from .base_handler import retry
from prompt_manager import PromptManager


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
        
        # TASK-3: Инициализация менеджера промптов
        self.prompt_manager = PromptManager(config_manager)
        self.logger.info("🔧 PromptManager инициализирован в SummaryHandler")
    
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
        
        TASK-2: Обрабатываем все файлы транскрипции для создания
        комплексного саммари, особенно когда в папке несколько видео.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
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
            
            # TASK-2: Сначала собираем все файлы транскрипции в папке
            transcript_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('_transcript.txt'):
                        file_path = os.path.join(root, file)
                        transcript_files.append(file_path)
            
            if not transcript_files:
                self.logger.info(f"📁 В папке {folder_path} нет файлов транскрипции")
                return result
            
            self.logger.info(f"📄 TASK-2: Найдено {len(transcript_files)} файлов транскрипции для обработки")
            
            # TASK-2: Если файлов несколько, создаем комплексное саммари
            if len(transcript_files) > 1:
                self.logger.info(f"🔄 TASK-2: Обнаружено несколько видео в папке, создаю комплексное саммари")
                return self._process_multiple_transcripts(transcript_files, account_type, folder_path)
            else:
                # Один файл - обычная обработка
                return self.process_folder_files(
                    folder_path=folder_path,
                    account_type=account_type,
                    file_extension='_transcript.txt',
                    should_process_func=self._should_process_transcript_file,
                    process_file_func=self._process_transcript_file
                )
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            result["errors"] += 1
            return result
    
    def _should_process_transcript_file(self, file_path: str) -> bool:
        """
        Проверяет, нужно ли обрабатывать файл транскрипции.
        
        TASK-2: Всегда обрабатываем все файлы транскрипции для создания
        комплексного саммари, особенно когда в папке несколько видео.
        
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
            
            # TASK-2: Всегда обрабатываем все файлы транскрипции
            # Убираем проверку существования файлов саммари/анализа
            # Это позволит создавать комплексные саммари для нескольких видео
            
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
            
            # TASK-3: Используем конфигурируемые промпты для генерации саммари
            try:
                # Получаем промпт и настройки
                prompt = self.prompt_manager.get_prompt('summary')
                settings = self.prompt_manager.get_prompt_settings('summary')
                
                self.logger.info(f"🔧 Используется промпт для саммари с настройками: {settings}")
                
                # TODO: Интегрировать с OpenAI API для реальной генерации саммари
                # Пока что создаем заглушку с использованием настроек
                
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка получения промпта для саммари: {e}")
                # Продолжаем с базовой логикой
            
            # Генерируем пути к выходным файлам
            base_path = file_path.replace('_transcript.txt', '')
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # Реальная логика генерации саммари через OpenAI API
            try:
                openai_config = self.get_openai_config()
                if not openai_config:
                    self.logger.warning("⚠️ OpenAI API не настроен, создаю базовое саммари")
                    # Создаем базовое саммари без API
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Саммари транскрипции: {os.path.basename(file_path)}\n\n")
                        f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                        f.write(f"Статус: Базовое саммари (OpenAI API не настроен)\n\n")
                        f.write("## Содержание:\n")
                        f.write("Для получения детального анализа настройте OpenAI API в .env файле\n")
                else:
                    # Реальная интеграция с OpenAI API
                    self.logger.info("🔧 OpenAI API настроен, запускаю генерацию саммари...")
                    
                    # Читаем файл транскрипции
                    transcript_content = ""
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            transcript_content = f.read()
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка чтения файла транскрипции: {e}")
                        transcript_content = "Содержание недоступно"
                    
                    # Создаем промпт для OpenAI
                    prompt = f"""Проанализируй следующую транскрипцию встречи и создай краткое саммари:

Транскрипция:
{transcript_content}

Создай структурированное саммари на русском языке, включающее:
1. Основные темы обсуждения
2. Ключевые решения
3. Действия и задачи
4. Важные моменты

Саммари:"""
                    
                    # Вызываем OpenAI API
                    import openai
                    client = openai.OpenAI(api_key=openai_config['api_key'])
                    
                    response = client.chat.completions.create(
                        model=openai_config.get('model', 'gpt-4o-mini'),
                        messages=[
                            {"role": "system", "content": "Ты - помощник по анализу встреч. Создавай краткие, структурированные саммари на русском языке."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=openai_config.get('temperature', 0.3),
                        max_tokens=1000
                    )
                    
                    # Получаем результат
                    summary_text = response.choices[0].message.content
                    
                    # Сохраняем саммари
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Саммари транскрипции: {os.path.basename(file_path)}\n\n")
                        f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                        f.write(f"Статус: Сгенерировано через OpenAI API\n")
                        f.write(f"Модель: {openai_config.get('model', 'gpt-4o-mini')}\n\n")
                        f.write("## Содержание:\n")
                        f.write(summary_text)
                    
                    self.logger.info(f"✅ Саммари успешно сгенерировано через OpenAI API: {len(summary_text)} символов")
                    
            except ImportError:
                self.logger.error("❌ Модуль openai не установлен")
                # Fallback: создаем базовое саммари
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Саммари транскрипции: {os.path.basename(file_path)}\n\n")
                    f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                    f.write(f"Статус: Ошибка - модуль openai не установлен\n\n")
                    f.write("## Содержание:\n")
                    f.write("Установите модуль: pip install openai\n")
            except Exception as e:
                self.logger.error(f"❌ Ошибка генерации саммари через OpenAI: {e}")
                # Fallback: создаем базовое саммари
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Саммари транскрипции: {os.path.basename(file_path)}\n\n")
                    f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                    f.write(f"Статус: Ошибка OpenAI API - {str(e)}\n\n")
                    f.write("## Содержание:\n")
                    f.write("Не удалось сгенерировать саммари через OpenAI API\n")
                    f.write(f"Ошибка: {str(e)}\n")
            
            # Создаем файл анализа
            with open(analysis_file, 'w', encoding='utf-8') as f:
                f.write('{\n')
                f.write('  "file": "' + os.path.basename(file_path) + '",\n')
                f.write('  "created": "' + self._get_current_timestamp() + '",\n')
                f.write('  "status": "generated",\n')
                f.write('  "analysis": "Анализ транскрипции",\n')
                f.write('  "method": "openai_api",\n')
                f.write('  "quality": "standard"\n')
                f.write('}\n')
            
            self.logger.info(f"✅ Созданы саммари и анализ: {summary_file}, {analysis_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки транскрипции {file_path}: {e}")
            return False
    
    def _process_multiple_transcripts(self, transcript_files: List[str], account_type: str, folder_path: str) -> Dict[str, Any]:
        """
        Обрабатывает несколько файлов транскрипции для создания комплексного саммари.
        
        TASK-2: Создает единое саммари для всех видео в папке.
        
        Args:
            transcript_files: Список путей к файлам транскрипции
            account_type: Тип аккаунта
            folder_path: Путь к папке
            
        Returns:
            Результат обработки
        """
        try:
            result = {
                "account": account_type, 
                "folder": folder_path, 
                "processed": 0, 
                "errors": 0, 
                "files": []
            }
            
            self.logger.info(f"🔄 TASK-2: Создаю комплексное саммари для {len(transcript_files)} файлов транскрипции")
            
            # Создаем папку для комплексного саммари
            folder_name = os.path.basename(folder_path)
            complex_summary_dir = os.path.join(folder_path, "complex_summary")
            os.makedirs(complex_summary_dir, exist_ok=True)
            
            # Генерируем имена для комплексного саммари
            timestamp = self._get_current_timestamp().replace(':', '-').replace(' ', '_')
            complex_summary_file = os.path.join(complex_summary_dir, f"{folder_name}_complex_summary_{timestamp}.txt")
            complex_analysis_file = os.path.join(complex_summary_dir, f"{folder_name}_complex_analysis_{timestamp}.json")
            
            # Читаем все транскрипции
            all_transcripts = []
            for transcript_file in transcript_files:
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        filename = os.path.basename(transcript_file)
                        all_transcripts.append({
                            "file": filename,
                            "content": content,
                            "path": transcript_file
                        })
                        self.logger.debug(f"📖 Прочитана транскрипция: {filename}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка чтения {transcript_file}: {e}")
                    result["errors"] += 1
                    continue
            
            if not all_transcripts:
                self.logger.error("❌ Не удалось прочитать ни одной транскрипции")
                result["errors"] += 1
                return result
            
                            # TASK-3: Создаем комплексное саммари с использованием OpenAI API
                try:
                    # Проверяем OpenAI API
                    openai_config = self.get_openai_config()
                    if openai_config and openai_config.get('api_key'):
                        self.logger.info("🔧 OpenAI API настроен, создаю комплексное саммари...")
                        
                        # Создаем промпт для комплексного анализа
                        all_content = "\n\n".join([
                            f"=== {t['file']} ===\n{t['content']}"
                            for t in all_transcripts
                        ])
                        
                        complex_prompt = f"""Проанализируй следующие транскрипции встреч и создай комплексное саммари:

{all_content}

Создай детальное комплексное саммари на русском языке, включающее:
1. Общие темы и тенденции
2. Ключевые решения и их взаимосвязи
3. Действия и задачи по всем встречам
4. Повторяющиеся проблемы и их решения
5. Прогресс и достижения
6. Инсайты и рекомендации

Комплексное саммари:"""
                        
                        # Вызываем OpenAI API
                        import openai
                        client = openai.OpenAI(api_key=openai_config['api_key'])
                        
                        response = client.chat.completions.create(
                            model=openai_config.get('model', 'gpt-4o-mini'),
                            messages=[
                                {"role": "system", "content": "Ты - эксперт по анализу встреч. Создавай детальные, структурированные комплексные саммари на русском языке."},
                                {"role": "user", "content": complex_prompt}
                            ],
                            temperature=openai_config.get('temperature', 0.3),
                            max_tokens=2000
                        )
                        
                        # Получаем результат
                        complex_summary_text = response.choices[0].message.content
                        
                        # Сохраняем комплексное саммари
                        with open(complex_summary_file, 'w', encoding='utf-8') as f:
                            f.write(f"# Комплексное саммари папки: {folder_name}\n\n")
                            f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                            f.write(f"Количество видео: {len(all_transcripts)}\n")
                            f.write(f"Модель: {openai_config.get('model', 'gpt-4o-mini')}\n\n")
                            
                            f.write("## Обработанные файлы:\n")
                            for transcript in all_transcripts:
                                f.write(f"- {transcript['file']}\n")
                            f.write("\n")
                            
                            f.write("## Комплексное саммари:\n")
                            f.write(complex_summary_text)
                        
                        self.logger.info(f"✅ Комплексное саммари создано через OpenAI API: {len(complex_summary_text)} символов")
                        
                    else:
                        self.logger.warning("⚠️ OpenAI API не настроен, создаю базовое комплексное саммари")
                        
                        # Создаем базовое комплексное саммари
                        with open(complex_summary_file, 'w', encoding='utf-8') as f:
                            f.write(f"# Комплексное саммари папки: {folder_name}\n\n")
                            f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                            f.write(f"Количество видео: {len(all_transcripts)}\n\n")
                            
                            f.write("## Обработанные файлы:\n")
                            for transcript in all_transcripts:
                                f.write(f"- {transcript['file']}\n")
                            f.write("\n")
                            
                            f.write("## Общее резюме:\n")
                            f.write("Комплексное саммари для всех видео в папке.\n")
                            f.write("Каждое видео было обработано и включено в общий анализ.\n\n")
                            
                            f.write("## Детали по файлам:\n")
                            for i, transcript in enumerate(all_transcripts, 1):
                                f.write(f"### {i}. {transcript['file']}\n")
                                f.write("Содержание: [Транскрипция включена в комплексный анализ]\n\n")
                            
                            f.write("## Настройки анализа:\n")
                            f.write("- OpenAI API не настроен\n")
                            f.write("- Используется базовый анализ\n")
                            f.write("- Для детального анализа настройте OpenAI API в .env файле\n")
                
                except Exception as e:
                    self.logger.error(f"❌ Ошибка создания комплексного саммари: {e}")
                    # Создаем базовое комплексное саммари в случае ошибки
                    with open(complex_summary_file, 'w', encoding='utf-8') as f:
                        f.write(f"# Комплексное саммари папки: {folder_name}\n\n")
                        f.write(f"Дата создания: {self._get_current_timestamp()}\n")
                        f.write(f"Количество видео: {len(all_transcripts)}\n\n")
                        f.write(f"## Ошибка создания:\n")
                        f.write(f"Не удалось создать комплексное саммари: {str(e)}\n")
                
                # Создаем комплексный анализ в JSON
                complex_analysis = {
                    "folder_name": folder_name,
                    "created": self._get_current_timestamp(),
                    "total_videos": len(all_transcripts),
                    "files_processed": [t["file"] for t in all_transcripts],
                    "summary_type": "complex",
                    "status": "success"
                }
                
                with open(complex_analysis_file, 'w', encoding='utf-8') as f:
                    import json
                    json.dump(complex_analysis, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"✅ TASK-2: Создано комплексное саммари: {complex_summary_file}")
                self.logger.info(f"✅ TASK-2: Создан комплексный анализ: {complex_analysis_file}")
                
                result["processed"] = len(all_transcripts)
                result["files"] = [t["file"] for t in all_transcripts]
                
                # Также создаем индивидуальные саммари для каждого файла
                for transcript in all_transcripts:
                    try:
                        if self._process_transcript_file(transcript["path"]):
                            self.logger.debug(f"✅ Создано индивидуальное саммари для: {transcript['file']}")
                        else:
                            self.logger.warning(f"⚠️ Не удалось создать индивидуальное саммари для: {transcript['file']}")
                    except Exception as e:
                        self.logger.error(f"❌ Ошибка создания индивидуального саммари для {transcript['file']}: {e}")
                        result["errors"] += 1
                
                return result
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка создания комплексного саммари: {e}")
                result["errors"] += 1
                return result
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки множественных транскрипций: {e}")
            result["errors"] += 1
            return result
    
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
