#!/usr/bin/env python3
"""
Модуль для транскрипции аудио файлов и генерации саммари
"""

import os
import sys
import re
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Добавляем путь к src для импорта модулей
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.config_manager import ConfigManager
    from src.transcript_analyzer import TranscriptAnalyzer
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Убедитесь, что все модули установлены")
    sys.exit(1)


class TranscriptionHandler:
    """Обработчик транскрипций аудио файлов."""
    
    def __init__(self, config_manager: ConfigManager, logger: Optional[logging.Logger] = None):
        """
        Инициализация обработчика транскрипций.
        
        Args:
            config_manager: Менеджер конфигурации
            logger: Логгер (опционально)
        """
        self.config_manager = config_manager
        self.logger = logger or logging.getLogger(__name__)
    
    def process_transcription(self) -> Dict[str, Any]:
        """
        Обработка транскрипции аудио файлов.
        
        Returns:
            Словарь с результатами обработки
        """
        try:
            self.logger.info("🎤 Начинаю обработку транскрипции аудио...")
            
            transcription_stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
            
            # Проверяем наличие аудио файлов перед запуском
            has_audio_files = False
            
            # Обрабатываем личный аккаунт
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Проверка аудио файлов в папке личного аккаунта: {personal_folder}")
                    personal_audio_files = self._count_audio_files(personal_folder)
                    if personal_audio_files > 0:
                        self.logger.info(f"🎵 Найдено {personal_audio_files} аудио файлов в личном аккаунте")
                        has_audio_files = True
                        self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                        personal_result = self._process_folder_transcription(personal_folder, "personal")
                        transcription_stats["details"].append(personal_result)
                        transcription_stats["processed"] += personal_result.get("processed", 0)
                        transcription_stats["errors"] += personal_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке личного аккаунта нет аудио файлов для транскрипции")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Проверка аудио файлов в папке рабочего аккаунта: {work_folder}")
                    work_audio_files = self._count_audio_files(work_folder)
                    if work_audio_files > 0:
                        self.logger.info(f"🎵 Найдено {work_audio_files} аудио файлов в рабочем аккаунте")
                        has_audio_files = True
                        self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                        work_result = self._process_folder_transcription(work_folder, "work")
                        transcription_stats["details"].append(work_result)
                        transcription_stats["processed"] += work_result.get("processed", 0)
                        transcription_stats["errors"] += work_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке рабочего аккаунта нет аудио файлов для транскрипции")
            
            if not has_audio_files:
                self.logger.info("📂 Нет аудио файлов для транскрипции")
                transcription_stats["status"] = "no_files"
            
            self.logger.info(f"✅ Транскрипция завершена: обработано {transcription_stats['processed']}, ошибок {transcription_stats['errors']}")
            
            return transcription_stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка транскрипции: {e}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            return error_stats
    
    def process_summaries(self) -> Dict[str, Any]:
        """
        Обработка саммари для транскрипций.
        
        Returns:
            Словарь с результатами обработки
        """
        try:
            self.logger.info("📝 Начинаю генерацию саммари для транскрипций...")
            
            summary_stats = {"status": "success", "processed": 0, "errors": 0, "details": []}
            
            # Проверяем наличие транскрипций перед запуском
            has_transcriptions = False
            
            # Обрабатываем личный аккаунт
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Проверка транскрипций в папке личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_summaries(personal_folder, "personal")
                    if personal_result["processed"] > 0:
                        has_transcriptions = True
                        summary_stats["details"].append(personal_result)
                        summary_stats["processed"] += personal_result.get("processed", 0)
                        summary_stats["errors"] += personal_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке личного аккаунта нет транскрипций для анализа")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Проверка транскрипций в папке рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_summaries(work_folder, "work")
                    if work_result["processed"] > 0:
                        has_transcriptions = True
                        summary_stats["details"].append(work_result)
                        summary_stats["processed"] += work_result.get("processed", 0)
                        summary_stats["errors"] += work_result.get("errors", 0)
                    else:
                        self.logger.info(f"📂 В папке рабочего аккаунта нет транскрипций для анализа")
            
            if not has_transcriptions:
                self.logger.info("📂 Нет транскрипций для анализа")
                summary_stats["status"] = "no_files"
            
            self.logger.info(f"✅ Генерация саммари завершена: обработано {summary_stats['processed']}, ошибок {summary_stats['errors']}")
            
            return summary_stats
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка генерации саммари: {e}")
            error_stats = {"status": "error", "processed": 0, "errors": 1, "details": [str(e)]}
            return error_stats
    
    def _count_audio_files(self, folder_path: str) -> int:
        """
        Подсчет количества аудио файлов для транскрипции.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Количество аудио файлов
        """
        try:
            count = 0
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.mp3') and not file.lower().endswith('_compressed.mp3'):
                        mp3_path = os.path.join(root, file)
                        transcript_file = mp3_path.replace('.mp3', '_transcript.txt')
                        if not os.path.exists(transcript_file):
                            count += 1
            return count
        except Exception as e:
            self.logger.error(f"❌ Ошибка подсчета аудио файлов: {e}")
            return 0
    
    def _process_folder_transcription(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Обработка транскрипции для конкретной папки.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
            
            # Ищем MP3 файлы для транскрипции
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('.mp3') and not file.lower().endswith('_compressed.mp3'):
                        mp3_path = os.path.join(root, file)
                        transcript_file = mp3_path.replace('.mp3', '_transcript.txt')
                        
                        # Пропускаем файлы, для которых уже есть транскрипция
                        if os.path.exists(transcript_file):
                            continue
                        
                        try:
                            self.logger.info(f"🎤 Транскрибирую: {file}")
                            
                            # Получаем настройки Whisper
                            whisper_config = self.config_manager.get_whisper_config()
                            model_type = whisper_config.get('model_type', 'base')
                            language = whisper_config.get('language', 'ru')
                            
                            # Формируем команду для запуска транскрипции через meeting_automation_universal.py
                            cmd = [
                                sys.executable,
                                'meeting_automation_universal.py',
                                'transcribe',
                                '--file', mp3_path,
                                '--model', model_type,
                                '--language', language
                            ]
                            
                            self.logger.info(f"🔄 Запуск команды: {' '.join(cmd)}")
                            
                            # Запускаем команду с таймаутом
                            process = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 минут
                            
                            if process.returncode == 0:
                                if os.path.exists(transcript_file):
                                    self.logger.info(f"✅ Транскрипция успешно создана: {os.path.basename(transcript_file)}")
                                    result["processed"] += 1
                                    result["files"].append({
                                        "file": os.path.basename(mp3_path),
                                        "output": os.path.basename(transcript_file),
                                        "status": "success"
                                    })
                                else:
                                    self.logger.error(f"❌ Транскрипция не создана, хотя команда выполнена успешно: {os.path.basename(mp3_path)}")
                                    result["errors"] += 1
                                    result["files"].append({
                                        "file": os.path.basename(mp3_path),
                                        "status": "error",
                                        "error": "Файл транскрипции не создан"
                                    })
                            else:
                                self.logger.error(f"❌ Ошибка транскрипции: {process.stderr}")
                                result["errors"] += 1
                                result["files"].append({
                                    "file": os.path.basename(mp3_path),
                                    "status": "error",
                                    "error": process.stderr
                                })
                                
                        except subprocess.TimeoutExpired:
                            self.logger.error(f"⏰ Таймаут транскрипции: {file}")
                            result["errors"] += 1
                            result["files"].append({
                                "file": os.path.basename(mp3_path),
                                "status": "error",
                                "error": "Timeout"
                            })
                        except Exception as e:
                            self.logger.error(f"❌ Ошибка транскрипции {file}: {e}")
                            result["errors"] += 1
                            result["files"].append({
                                "file": os.path.basename(mp3_path),
                                "status": "error",
                                "error": str(e)
                            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}
    
    def _process_folder_summaries(self, folder_path: str, account_type: str) -> Dict[str, Any]:
        """
        Обработка саммари для транскрипций в конкретной папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            
        Returns:
            Словарь с результатами обработки
        """
        try:
            result = {"account": account_type, "folder": folder_path, "processed": 0, "errors": 0, "files": []}
            
            # Ищем файлы транскрипций для анализа
            transcript_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith('_transcript.txt'):
                        # Проверяем, существует ли уже файл саммари
                        transcript_path = os.path.join(root, file)
                        summary_file = transcript_path.replace('_transcript.txt', '_summary.txt')
                        analysis_file = transcript_path.replace('_transcript.txt', '_analysis.json')
                        
                        # Если саммари или анализ уже существуют, пропускаем файл
                        if os.path.exists(summary_file) or os.path.exists(analysis_file):
                            continue
                        
                        transcript_files.append(transcript_path)
            
            if not transcript_files:
                self.logger.info(f"📁 В папке {folder_path} нет новых транскрипций для анализа")
                return result
            
            self.logger.info(f"📄 Найдено {len(transcript_files)} транскрипций для анализа")
            
            # Получаем настройки OpenAI
            openai_config = self.config_manager.get_openai_config()
            openai_api_key = openai_config.get('api_key')
            
            if not openai_api_key:
                self.logger.error("❌ Не настроен API ключ OpenAI")
                result["errors"] += 1
                return result
            
            # Инициализируем анализатор транскрипций
            analyzer = TranscriptAnalyzer(
                api_key=openai_api_key,
                model=openai_config.get('analysis_model', 'gpt-4o-mini')
            )
            
            # Обрабатываем каждую транскрипцию
            for transcript_path in transcript_files:
                try:
                    file_name = os.path.basename(transcript_path)
                    self.logger.info(f"📝 Анализирую транскрипцию: {file_name}")
                    
                    # Извлекаем название и дату встречи из имени файла
                    meeting_title = ""
                    meeting_date = ""
                    
                    # Пытаемся извлечь дату из имени файла
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', file_name)
                    if date_match:
                        meeting_date = date_match.group(1)
                    
                    # Пытаемся извлечь название встречи
                    if meeting_date:
                        title_match = re.search(rf'{meeting_date}.*?_transcript\.txt', file_name)
                        if title_match:
                            meeting_title = title_match.group(0).replace(f"{meeting_date} ", "").replace("_transcript.txt", "")
                    
                    # Читаем транскрипцию
                    with open(transcript_path, 'r', encoding='utf-8') as f:
                        transcript_text = f.read()
                    
                    # Анализируем транскрипцию
                    analysis_result = analyzer.analyze_meeting_transcript(
                        transcript=transcript_text,
                        meeting_title=meeting_title,
                        meeting_date=meeting_date
                    )
                    
                    # Сохраняем результат анализа в JSON
                    analysis_file = transcript_path.replace('_transcript.txt', '_analysis.json')
                    with open(analysis_file, 'w', encoding='utf-8') as f:
                        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
                    
                    # Создаем текстовое саммари
                    summary_file = transcript_path.replace('_transcript.txt', '_summary.txt')
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        summary = analysis_result.get('meeting_summary', {})
                        f.write(f"# {summary.get('title', 'Встреча')}\n\n")
                        f.write(f"Дата: {meeting_date}\n\n")
                        f.write(f"## Основная тема\n{summary.get('main_topic', 'Не указана')}\n\n")
                        
                        # Ключевые решения
                        f.write("## Ключевые решения\n")
                        for decision in summary.get('key_decisions', []):
                            f.write(f"- {decision}\n")
                        f.write("\n")
                        
                        # Действия
                        f.write("## Действия\n")
                        for action in summary.get('action_items', []):
                            f.write(f"- {action}\n")
                        f.write("\n")
                        
                        # Следующие шаги
                        f.write("## Следующие шаги\n")
                        for step in summary.get('next_steps', []):
                            f.write(f"- {step}\n")
                        f.write("\n")
                        
                        # Участники
                        f.write("## Участники\n")
                        for participant in summary.get('participants', []):
                            f.write(f"- {participant}\n")
                    
                    result["processed"] += 1
                    result["files"].append({
                        "file": file_name,
                        "status": "success",
                        "output": os.path.basename(summary_file)
                    })
                    
                    self.logger.info(f"✅ Анализ завершен: {file_name}")
                    
                except Exception as e:
                    result["errors"] += 1
                    result["files"].append({
                        "file": os.path.basename(transcript_path),
                        "status": "error",
                        "error": str(e)
                    })
                    self.logger.error(f"❌ Ошибка анализа {os.path.basename(transcript_path)}: {e}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            return {"account": account_type, "folder": folder_path, "processed": 0, "errors": 1, "files": [], "error": str(e)}


def get_transcription_handler(config_manager: ConfigManager, logger: Optional[logging.Logger] = None) -> TranscriptionHandler:
    """
    Получение обработчика транскрипций.
    
    Args:
        config_manager: Менеджер конфигурации
        logger: Логгер (опционально)
        
    Returns:
        Обработчик транскрипций
    """
    return TranscriptionHandler(config_manager, logger)
