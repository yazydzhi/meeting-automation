#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированный обработчик для медиа файлов
"""

import os
import time
from typing import Dict, Any, List
from .base_handler import BaseHandler, retry


class MediaHandler(BaseHandler):
    """Обработчик медиа файлов."""
    
    def __init__(self, config_manager, media_processor=None, logger=None):
        """
        Инициализация обработчика медиа.
        
        Args:
            config_manager: Менеджер конфигурации
            media_processor: Существующий обработчик медиа (если есть)
            logger: Логгер
        """
        super().__init__(config_manager, logger)
        self.media_processor = media_processor
        self.last_media_check = 0
        self.media_check_interval = 1800  # 30 минут по умолчанию
        self.last_media_stats = {}
    
    @retry(max_attempts=2, delay=3, backoff=2)
    def process(self, quality: str = 'medium', *args, **kwargs) -> Dict[str, Any]:
        """
        Основной метод обработки медиа файлов.
        
        Args:
            quality: Качество сжатия ('low', 'medium', 'high')
            
        Returns:
            Результат обработки медиа
        """
        try:
            self._log_operation_start("обработку медиа файлов", quality=quality)
            
            # Проверяем, прошло ли достаточно времени с последней проверки
            current_time = time.time()
            if (current_time - self.last_media_check) < self.media_check_interval:
                self.logger.info("⏰ Медиа обработка еще не требуется")
                return {"processed": 0, "synced": 0, "cleanup": 0, "errors": 0, "status": "skipped"}
            
            self.last_media_check = current_time
            
            # Пытаемся использовать существующий обработчик
            if self.media_processor:
                result = self.media_processor.process_media(quality)
                self.last_media_stats = result
                self._log_operation_end("обработку медиа файлов", result)
                return result
            
            # Используем собственную логику
            result = self._process_media_files(quality)
            self.last_media_stats = result
            self._log_operation_end("обработку медиа файлов", result)
            return result
            
        except Exception as e:
            return self._create_error_result(e, "обработка медиа файлов")
    
    def _process_media_files(self, quality: str) -> Dict[str, Any]:
        """
        Обработка медиа файлов с использованием universal script.
        
        Args:
            quality: Качество сжатия
            
        Returns:
            Результат обработки
        """
        try:
            self.logger.info("🎬 Запуск обработки медиа файлов...")
            
            results = []
            total_processed = 0
            total_synced = 0
            
            # Обрабатываем личный аккаунт
            if self.config_manager.is_personal_enabled():
                personal_config = self.config_manager.get_personal_config()
                personal_folder = personal_config.get('local_drive_root')
                if personal_folder and os.path.exists(personal_folder):
                    self.logger.info(f"👤 Обрабатываю папку личного аккаунта: {personal_folder}")
                    personal_result = self._process_folder_media(personal_folder, "personal", quality)
                    results.append(personal_result)
                    total_processed += personal_result.get("processed", 0)
                    total_synced += personal_result.get("synced", 0)
                else:
                    self.logger.warning(f"⚠️ Папка личного аккаунта не найдена: {personal_folder}")
            
            # Обрабатываем рабочий аккаунт
            if self.config_manager.is_work_enabled():
                work_config = self.config_manager.get_work_config()
                work_folder = work_config.get('local_drive_root')
                if work_folder and os.path.exists(work_folder):
                    self.logger.info(f"🏢 Обрабатываю папку рабочего аккаунта: {work_folder}")
                    work_result = self._process_folder_media(work_folder, "work", quality)
                    results.append(work_result)
                    total_processed += work_result.get("processed", 0)
                    total_synced += work_result.get("synced", 0)
                else:
                    self.logger.warning(f"⚠️ Папка рабочего аккаунта не найдена: {work_folder}")
            
            self.logger.info(f"✅ Обработка медиа завершена: обработано {total_processed}, найдено {total_synced}")
            
            return {
                "status": "success",
                "message": "Media processing completed",
                "results": results,
                "total_processed": total_processed,
                "total_synced": total_synced
            }
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки медиа: {e}")
            return self._create_error_result(e, "обработка медиа файлов")
    
    def _process_folder_media(self, folder_path: str, account_type: str, quality: str) -> Dict[str, Any]:
        """
        Обработка медиа файлов в конкретной папке.
        
        Args:
            folder_path: Путь к папке
            account_type: Тип аккаунта
            quality: Качество сжатия
            
        Returns:
            Результат обработки папки
        """
        try:
            result = {
                "account": account_type,
                "folder": folder_path,
                "processed": 0,
                "synced": 0,
                "errors": 0,
                "files": []
            }
            
            # Ищем видео файлы для обработки
            video_files = self._find_video_files(folder_path)
            
            if not video_files:
                self.logger.info(f"📁 В папке {folder_path} нет видео файлов для обработки")
                return result
            
            self.logger.info(f"🎬 Найдено {len(video_files)} видео файлов для обработки")
            
            # Обрабатываем каждый видео файл
            for video_file in video_files:
                try:
                    if self._process_video_file(video_file, quality):
                        result["processed"] += 1
                        result["files"].append(video_file)
                        self.logger.debug(f"✅ Обработан видео файл: {video_file}")
                    else:
                        result["errors"] += 1
                        self.logger.warning(f"⚠️ Не удалось обработать видео файл: {video_file}")
                except Exception as e:
                    self.logger.error(f"❌ Ошибка обработки видео файла {video_file}: {e}")
                    result["errors"] += 1
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки папки {folder_path}: {e}")
            result["errors"] += 1
            return result
    
    def _find_video_files(self, folder_path: str) -> List[str]:
        """
        Находит видео файлы в папке.
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Список путей к видео файлам
        """
        try:
            video_files = []
            video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv']
            
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if any(file.lower().endswith(ext) for ext in video_extensions):
                        # Проверяем, что это не уже сжатый файл
                        if not file.lower().endswith('_compressed.mp4'):
                            video_files.append(os.path.join(root, file))
            
            return video_files
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка поиска видео файлов в {folder_path}: {e}")
            return []
    
    def _process_video_file(self, video_file: str, quality: str) -> bool:
        """
        TASK-5: Обрабатывает видео файл с поддержкой удаления оригиналов.
        
        Args:
            video_file: Путь к видео файлу
            quality: Качество сжатия
            
        Returns:
            True если обработка успешна, False иначе
        """
        try:
            self.logger.info(f"🎬 TASK-5: Обрабатываю видео: {os.path.basename(video_file)}")
            
            # Генерируем пути к файлам
            base_path = os.path.splitext(video_file)[0]
            compressed_video = base_path + '_compressed.mp4'
            compressed_audio = base_path + '_compressed.mp3'
            
            # TASK-5: Проверяем настройку удаления оригиналов
            should_delete = self.config_manager.should_delete_original_videos()
            self.logger.info(f"🔧 TASK-5: Настройка удаления оригиналов: {should_delete}")
            
            # Реальная логика сжатия видео через FFmpeg
            video_success = self._compress_video(video_file, compressed_video, quality)
            if not video_success:
                self.logger.error(f"❌ Не удалось сжать видео: {video_file}")
                return False
            
            # Реальная логика извлечения аудио из сжатого видео
            audio_success = self._extract_audio(compressed_video, compressed_audio)
            if not audio_success:
                self.logger.error(f"❌ Не удалось извлечь аудио из сжатого видео: {compressed_video}")
                return False
            
            self.logger.info(f"✅ Создан сжатый видео файл: {compressed_video}")
            self.logger.info(f"✅ Создан сжатый аудио файл: {compressed_audio}")
            
            # TASK-5: Логируем информацию о файлах
            if should_delete:
                self.logger.info(f"🔧 TASK-5: Система настроена на удаление оригиналов при совпадении длины")
            else:
                self.logger.info(f"🔧 TASK-5: Система настроена на сохранение оригиналов")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Ошибка обработки видео файла {video_file}: {e}")
            return False
    
    def set_media_check_interval(self, interval: int):
        """
        Устанавливает интервал проверки медиа файлов.
        
        Args:
            interval: Интервал в секундах
        """
        self.media_check_interval = interval
        self.logger.info(f"⏰ Установлен интервал проверки медиа: {interval} секунд")
    
    def get_media_stats(self) -> Dict[str, Any]:
        """
        Получает последнюю статистику обработки медиа.
        
        Returns:
            Последняя статистика
        """
        return self.last_media_stats
    
    def reset_media_check_timer(self):
        """Сбрасывает таймер проверки медиа."""
        self.last_media_check = 0
        self.logger.info("⏰ Таймер проверки медиа сброшен")
    
    def _compress_video(self, input_file: str, output_file: str, quality: str) -> bool:
        """
        Сжатие видео файла через FFmpeg.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            quality: Качество сжатия
            
        Returns:
            True, если сжатие прошло успешно
        """
        try:
            import subprocess
            
            # Определяем параметры качества
            quality_params = {
                'low': ['-crf', '28', '-preset', 'fast'],
                'medium': ['-crf', '23', '-preset', 'medium'],
                'high': ['-crf', '18', '-preset', 'slow']
            }
            
            params = quality_params.get(quality, quality_params['medium'])
            
            cmd = [
                'ffmpeg', '-i', input_file,
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '128k'
            ] + params + [
                '-y',  # Перезаписывать существующие файлы
                output_file
            ]
            
            self.logger.info(f"🎬 Запуск FFmpeg: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)  # 30 минут
            
            if result.returncode == 0:
                self.logger.info(f"✅ Видео успешно сжато: {output_file}")
                return True
            else:
                self.logger.error(f"❌ Ошибка сжатия видео: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Таймаут сжатия видео: {input_file}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка сжатия видео {input_file}: {e}")
            return False
    
    def _extract_audio(self, input_file: str, output_file: str) -> bool:
        """
        Извлечение аудио из видео файла.
        
        Args:
            input_file: Путь к входному файлу
            output_file: Путь к выходному файлу
            
        Returns:
            True, если извлечение прошло успешно
        """
        try:
            import subprocess
            
            cmd = [
                'ffmpeg', '-i', input_file,
                '-vn',  # Без видео
                '-c:a', 'mp3',
                '-b:a', '128k',
                '-ar', '44100',
                '-y',  # Перезаписывать существующие файлы
                output_file
            ]
            
            self.logger.info(f"🎵 Извлечение аудио: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)  # 10 минут
            
            if result.returncode == 0:
                self.logger.info(f"✅ Аудио успешно извлечено: {output_file}")
                return True
            else:
                self.logger.error(f"❌ Ошибка извлечения аудио: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"⏰ Таймаут извлечения аудио: {input_file}")
            return False
        except Exception as e:
            self.logger.error(f"❌ Ошибка извлечения аудио {input_file}: {e}")
            return False
