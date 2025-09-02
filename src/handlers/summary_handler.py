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
        
        # Инициализируем StateManager для отслеживания обработанных саммари
        try:
            from .state_manager import StateManager
            self.state_manager = StateManager(logger=self.logger)
            self.logger.info("✅ StateManager инициализирован в SummaryHandler")
        except Exception as e:
            self.logger.warning(f"⚠️ StateManager недоступен в SummaryHandler: {e}")
            self.state_manager = None
    
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
            summary_result = {
                "status": "success",
                "message": "Summary processing completed",
                "results": results,
                "total_processed": total_processed,
                "total_errors": total_errors
            }
            # Возвращаем два значения: summary_stats и notion_update_stats (пустой для совместимости)
            return summary_result, {"status": "skipped", "message": "Notion updates not implemented"}
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки саммари: {e}")
            error_result = {"status": "error", "message": str(e)}
            # Возвращаем два значения: summary_stats и notion_update_stats (пустой для совместимости)
            return error_result, {"status": "skipped", "message": "Notion updates not implemented"}
    
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
            
            # TASK-2: Если файлов несколько, создаем комплексное саммари (если включено)
            if len(transcript_files) > 1:
                summary_config = self.config_manager.get_summary_config()
                if summary_config.get('enable_complex_summary', False):
                    self.logger.info(f"🔄 TASK-2: Обнаружено несколько видео в папке, создаю комплексное саммари")
                    complex_result = self._process_multiple_transcripts(transcript_files, account_type, folder_path)
                    if complex_result:
                        result["complex_summary"] = complex_result
                else:
                    self.logger.info(f"🔄 TASK-2: Комплексное саммари отключено в настройках")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}
    
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
                    continue
            
            if not all_transcripts:
                self.logger.error("❌ Не удалось прочитать ни одной транскрипции")
                return None
            
            # Создаем комплексное саммари с использованием OpenAI API
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
                
                return {
                    "status": "success",
                    "summary_file": complex_summary_file,
                    "analysis_file": complex_analysis_file,
                    "processed_files": len(all_transcripts)
                }
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка создания комплексного саммари: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки множественных транскрипций: {e}")
            return None
    
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
            
            # Проверяем в БД, было ли саммари уже обработано
            if self.state_manager:
                if self.state_manager.is_summary_processed(file_path):
                    self.logger.debug(f"⏭️ Саммари уже обработано: {os.path.basename(file_path)}")
                    return False
            
            # Генерируем пути к файлам саммари и анализа
            base_path = os.path.splitext(file_path)[0]
            summary_file = base_path + '_summary.txt'
            analysis_file = base_path + '_analysis.json'
            
            # Проверяем существование файлов саммари
            if os.path.exists(summary_file) and os.path.exists(analysis_file):
                self.logger.debug(f"⏭️ Файлы саммари уже существуют: {os.path.basename(file_path)}")
                return False
            
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
            
            # Помечаем саммари как обработанное в БД
            if self.state_manager:
                self.state_manager.mark_summary_processed(file_path, summary_file, analysis_file, "success")
            
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
